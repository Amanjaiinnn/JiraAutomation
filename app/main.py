


import streamlit as st

from analysis.duplicate_detector import detect_duplicates
from codegen.code_generator import SUPPORTED_STACKS, generate_code_for_story
from ingestion.chunker import chunk_requirements
from ingestion.loader import load_requirements
from jira_integration.story_creator import create_jira_stories
from llms.epic_llm import regenerate_epic
from llms.epic_pipeline import generate_epics_from_requirements
from llms.reducer import merge_and_dedupe
from llms.story_llm import generate_stories_from_chunk, regenerate_story
from rag.retriever import retrieve_top_k


st.set_page_config(page_title="Jira AI Automation", layout="wide")
st.title("🚀 Jira AI Automation")


def _ensure_state():
    st.session_state.setdefault("chunks", [])
    st.session_state.setdefault("epics", {})
    st.session_state.setdefault("generated_code", {})


def _init_epics(epics):
    st.session_state.epics = {}
    for idx, epic in enumerate(epics, start=1):
        eid = f"E{idx}"
        st.session_state.epics[eid] = {
            "epic_name": epic["epic_name"],
            "description": epic["description"],
            "covered_requirements": epic.get("covered_requirements", []),
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
            epics = generate_epics_from_requirements(st.session_state.chunks)
        _init_epics(epics)


if st.session_state.epics:
    st.subheader("🧩 Epics (editable + controllable)")

    for epic_id, epic in st.session_state.epics.items():
        with st.container(border=True):
            st.markdown(f"### {epic_id}")
            epic["epic_name"] = st.text_input("Epic Name", epic["epic_name"], key=f"epic_name_{epic_id}")
            epic["description"] = st.text_area("Epic Description", epic["description"], key=f"epic_desc_{epic_id}")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 Re-generate Epic", key=f"regen_epic_{epic_id}"):
                    source = "\n".join(epic.get("covered_requirements", [])) or epic["description"]
                    with st.spinner("Regenerating selected epic only..."):
                        updated = regenerate_epic(source, epic["epic_name"])
                    epic["epic_name"] = updated["epic_name"]
                    epic["description"] = updated["description"]

            with c2:
                if st.button("📄 Generate Stories for this Epic", key=f"gen_stories_{epic_id}"):
                    with st.spinner("Generating stories for selected epic..."):
                        epic_chunks = retrieve_top_k(st.session_state.chunks, epic["epic_name"], k=4)
                        stories = []
                        for chunk in epic_chunks:
                            stories.extend(generate_stories_from_chunk(epic, chunk))
                        merged = merge_and_dedupe(stories)
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
                        story["selected"] = st.checkbox("Create in Jira", value=story["selected"], key=f"sel_{epic_id}_{story_id}")
                        story["summary"] = st.text_input("Summary", story["summary"], key=f"sum_{epic_id}_{story_id}")
                        story["description"] = st.text_area("Description", story.get("description", ""), key=f"desc_{epic_id}_{story_id}")
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

                        dups = detect_duplicates(story)
                        if dups:
                            duplicates_found = True
                            st.warning("Possible duplicates")
                            for dup in dups:
                                st.write(f"- {dup['jira_key']} ({dup['similarity']})")

                        stack = st.selectbox(
                            "Tech Stack",
                            options=list(SUPPORTED_STACKS.keys()),
                            format_func=lambda k: SUPPORTED_STACKS[k]["label"],
                            key=f"stack_{epic_id}_{story_id}",
                        )
                        if st.button("⚙️ Generate Code", key=f"code_{epic_id}_{story_id}"):
                            st.session_state.generated_code[(epic_id, story_id)] = generate_code_for_story(story, stack)

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