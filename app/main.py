import streamlit as st

from api_client import (
    check_duplicates,
    create_jira_stories,
    generate_code,
    generate_epics,
    generate_stories,
    regenerate_epic,
    regenerate_story,
)
from codegen.code_generator import SUPPORTED_STACKS
from ingestion.chunker import chunk_requirements
from ingestion.loader import load_requirements


st.set_page_config(page_title="Jira AI Automation", layout="wide")
st.title("🚀 Jira AI Automation")


def _ensure_state():
    st.session_state.setdefault("chunks", [])
    st.session_state.setdefault("epics", {})
    st.session_state.setdefault("generated_code", {})
    st.session_state.setdefault("duplicate_results", {})


def _init_epics(epics):
    st.session_state.epics = {}
    for idx, epic in enumerate(epics, start=1):
        eid = f"E{idx}"
        st.session_state.epics[eid] = {
            "epic_name": epic["epic_name"],
            "summary": epic.get("summary", ""),
            "description": epic["description"],
            "business_objectives": epic.get("business_objectives", []),
            "scope": epic.get("scope", {"in_scope": [], "out_of_scope": []}),
            "acceptance_criteria": epic.get("acceptance_criteria", []),
            "definition_of_done": epic.get("definition_of_done", []),
            "covered_requirements": epic.get("covered_requirements", []),
            "source_chunk_ids": epic.get("source_chunk_ids", []),
            "locked": False,
            "stories": {},
        }


_ensure_state()
uploaded = st.file_uploader("Upload requirements (CSV / PDF / TXT)")

if uploaded:
    requirements_text = load_requirements(uploaded)
    st.session_state.chunks = chunk_requirements(requirements_text)
    st.info(f"Total semantic chunks: {len(st.session_state.chunks)}")

    if st.button("🧩 Generate Epics", use_container_width=True):
        with st.spinner("Running MAP-REDUCE epic generation..."):
            epics = generate_epics(st.session_state.chunks)
        _init_epics(epics)


if st.session_state.epics:
    st.subheader("🧩 Epics (editable + controllable)")

    for epic_id, epic in st.session_state.epics.items():
        with st.container(border=True):
            st.markdown(f"### {epic_id}")
            epic["epic_name"] = st.text_input("Epic Name", epic["epic_name"], key=f"epic_name_{epic_id}")
            epic["description"] = st.text_area("Epic Description", epic["description"], key=f"epic_desc_{epic_id}")

            if epic.get("summary"):
                st.caption(epic["summary"])
            with st.expander("Epic details", expanded=False):
                if epic.get("business_objectives"):
                    st.markdown("**Business Objectives**")
                    for item in epic.get("business_objectives", []):
                        st.write(f"- {item}")
                scope = epic.get("scope", {})
                if scope.get("in_scope") or scope.get("out_of_scope"):
                    st.markdown("**Scope**")
                    if scope.get("in_scope"):
                        st.write("In scope:")
                        for item in scope.get("in_scope", []):
                            st.write(f"- {item}")
                    if scope.get("out_of_scope"):
                        st.write("Out of scope:")
                        for item in scope.get("out_of_scope", []):
                            st.write(f"- {item}")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 Re-generate Epic", key=f"regen_epic_{epic_id}"):
                    source_chunks = [
                        c["text"] for c in st.session_state.chunks if c["chunk_id"] in epic.get("source_chunk_ids", [])
                    ]
                    source = "\n\n".join(source_chunks) or "\n".join(epic.get("covered_requirements", [])) or epic["description"]
                    with st.spinner("Regenerating selected epic only..."):
                        updated = regenerate_epic(source, epic["epic_name"], previous_description=epic["description"])
                    epic["epic_name"] = updated["epic_name"]
                    epic["description"] = updated["description"]

            with c2:
                if st.button("📄 Generate Stories for this Epic", key=f"gen_stories_{epic_id}"):
                    with st.spinner("Generating stories for selected epic..."):
                        merged = generate_stories(epic, st.session_state.chunks, top_k=4)
                    epic["stories"] = {
                        f"S{i+1}": {
                            **story,
                            "selected": False,
                            "locked": False,
                        }
                        for i, story in enumerate(merged)
                    }

            if epic["stories"]:
                st.markdown("#### Stories")
                duplicates_found = False
                for story_id, story in epic["stories"].items():
                    with st.expander(f"{story_id}: {story['summary']}"):
                        story_tabs = st.tabs(["Story", "Duplicate Story Tag", "Code Generation"])

                        with story_tabs[0]:
                            story["selected"] = st.checkbox(
                                "Create in Jira", value=story["selected"], key=f"sel_{epic_id}_{story_id}"
                            )
                            story["summary"] = st.text_input("Summary", story["summary"], key=f"sum_{epic_id}_{story_id}")
                            story["description"] = st.text_area(
                                "Description", story.get("description", ""), key=f"desc_{epic_id}_{story_id}"
                            )
                            story["acceptance_criteria"] = st.text_area(
                                "Acceptance criteria (one per line)",
                                "\n".join(story.get("acceptance_criteria", [])),
                                key=f"ac_{epic_id}_{story_id}",
                            ).splitlines()
                            story["definition_of_done"] = st.text_area(
                                "Definition of done (one per line)",
                                "\n".join(story.get("definition_of_done", [])),
                                key=f"dod_{epic_id}_{story_id}",
                            ).splitlines()

                            if st.button("🔁 Re-generate Story", key=f"regen_story_{epic_id}_{story_id}"):
                                chunk_id = story.get("source_chunk_id")
                                source_chunk = next((c for c in st.session_state.chunks if c["chunk_id"] == chunk_id), None)
                                source = source_chunk["text"] if source_chunk else epic["description"]
                                story.update(regenerate_story(story, source))

                        with story_tabs[1]:
                            st.markdown("**Generated Story for Duplicate Check**")
                            st.write(f"Summary: {story.get('summary', '')}")
                            st.write(f"Description: {story.get('description', '')}")

                            if st.button("🔍 Check Duplicates", key=f"dups_{epic_id}_{story_id}"):
                                st.session_state.duplicate_results[(epic_id, story_id)] = check_duplicates(story)

                            dups = st.session_state.duplicate_results.get((epic_id, story_id), [])
                            if dups:
                                duplicates_found = True
                                st.warning("Possible duplicates")
                                for dup in dups:
                                    st.write(f"- {dup['jira_key']} ({dup['similarity']})")
                            elif (epic_id, story_id) in st.session_state.duplicate_results:
                                st.success("No duplicates found for this story.")

                        with story_tabs[2]:
                            st.markdown("**Story for Code Generation**")
                            st.write(f"Summary: {story.get('summary', '')}")
                            st.write(f"Description: {story.get('description', '')}")

                            stack = st.selectbox(
                                "Tech Stack",
                                options=list(SUPPORTED_STACKS.keys()),
                                format_func=lambda k: SUPPORTED_STACKS[k]["label"],
                                key=f"stack_{epic_id}_{story_id}",
                            )
                            if st.button("⚙️ Generate Code", key=f"code_{epic_id}_{story_id}"):
                                st.session_state.generated_code[(epic_id, story_id)] = generate_code(story, stack)

                            if (epic_id, story_id) in st.session_state.generated_code:
                                for filename, code in st.session_state.generated_code[(epic_id, story_id)].items():
                                    st.code(code, language=filename.split(".")[-1])

                override_duplicates = True
                if duplicates_found:
                    override_duplicates = st.checkbox(
                        "I understand duplicates may exist. Create Jira issues anyway.",
                        key=f"override_{epic_id}",
                    )

                if st.button("🚀 Create Selected Stories in Jira", key=f"jira_{epic_id}"):
                    selected = [s for s in epic["stories"].values() if s.get("selected")]
                    if not selected:
                        st.warning("No stories selected.")
                    elif not override_duplicates:
                        st.error("Resolve duplicates or acknowledge risk.")
                    else:
                        keys = create_jira_stories(selected)
                        st.success("Created Jira issues")
                        for key in keys:
                            st.write(f"- {key}")