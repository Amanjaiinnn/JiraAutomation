
# import streamlit as st

# from ingestion.loader import load_requirements
# from ingestion.chunker import chunk_requirements
# from rag.retriever import retrieve_top_k
# from llms.story_llm import generate_stories_from_chunk
# from llms.reducer import merge_and_dedupe
# from jira_integration.story_creator import create_jira_stories
# from analysis.duplicate_detector import detect_duplicates
# from codegen.code_generator import generate_code_for_story, SUPPORTED_STACKS
# from llms.epic_llm import generate_epics, regenerate_epic
# import uuid


# st.set_page_config(page_title="Jira AI Automation", layout="wide")
# st.title(" Jira AI Automation ")

# uploaded = st.file_uploader("Upload requirements (CSV / PDF / TXT)")

# if uploaded:
#     text = load_requirements(uploaded)
#     chunks = chunk_requirements(text)

#     st.info(f"Total chunks: {len(chunks)}")

#     query = st.text_input(
#         "What do you want to generate stories for?",
#         value="core functionality"
#     )

#     top_chunks = retrieve_top_k(chunks, query)

#     if st.button("Generate Stories"):
#         stories = []
#         for i, chunk in enumerate(top_chunks):
#             stories.extend(generate_stories_from_chunk(chunk, i))

#         final_stories = merge_and_dedupe(stories)
#         st.session_state.stories = final_stories





# # =========================
# # Review Generated Stories
# # =========================
# if "stories" in st.session_state and st.session_state.stories:
#     st.subheader("📝 Generated Stories (Review before Jira creation)")

#     from collections import defaultdict
#     epics = defaultdict(list)

#     # Group stories by epic
#     for s in st.session_state.stories:
#         epics[s["epic_name"]].append(s)

#     # 🔹 Review UI: Epic → Stories → Details
#     for epic, stories in epics.items():
#         st.markdown(f"## 🧩 Epic: {epic}")

#         for idx, story in enumerate(stories, start=1):
#             with st.expander(f"📌 {idx}. {story['summary']}"):
#                 st.markdown("**Description**")
#                 st.write(story.get("description", ""))

#                 st.markdown("**Acceptance Criteria**")
#                 for ac in story.get("acceptance_criteria", []):
#                     st.write(f"- {ac}")

#                 st.markdown("**Definition of Done**")
#                 for dod in story.get("definition_of_done", []):
#                     st.write(f"- {dod}")

#     st.warning(
#         "⚠️ Please review Epics, Stories, Acceptance Criteria, and Definition of Done before creating Jira issues."
#     )
#     st.subheader("🔍 Duplicate Ticket Check")

#     duplicate_map = {}

#     for story in st.session_state.stories:
#         duplicates = detect_duplicates(story)

#         if duplicates:
#             duplicate_map[story["summary"]] = duplicates
#             st.warning(f"⚠️ Possible duplicates for: {story['summary']}")

#             for d in duplicates:
#                 st.write(
#                     f"- {d['jira_key']} (similarity: {d['similarity']})"
#             )

#     if duplicate_map:
#         st.error(
#             "Duplicates detected. Review carefully before creating Jira issues."
#     )
#     force_create = st.checkbox(
#         "I understand duplicates may exist. Create Jira issues anyway."
#     )    

#     # =========================
# # Code Generation Per Story
# # =========================
# if "stories" in st.session_state and st.session_state.stories:
#     st.subheader("🧠 Generate Code per Story")

#     if "generated_code" not in st.session_state:
#         st.session_state.generated_code = {}

#     for idx, story in enumerate(st.session_state.stories):
#         st.markdown(f"### 🧩 {story['summary']}")

#         col1, col2 = st.columns([1, 2])

#         with col1:
#             stack_key = st.selectbox(
#                 "Choose Tech Stack",
#                 options=list(SUPPORTED_STACKS.keys()),
#                 format_func=lambda k: SUPPORTED_STACKS[k]["label"],
#                 key=f"stack_{idx}"
#             )

#             if st.button("⚙️ Generate Code", key=f"gen_{idx}"):
#                 with st.spinner("Generating code..."):
#                     files = generate_code_for_story(story, stack_key)
#                     st.session_state.generated_code[idx] = files

#         # Show generated code
#         if idx in st.session_state.generated_code:
#             for filename, code in st.session_state.generated_code[idx].items():
#                 with st.expander(f"📄 {filename}"):
#                     st.code(code, language=filename.split(".")[-1])


#     if st.button("🚀 Create in Jira"):
#         keys = create_jira_stories(st.session_state.stories)
#         st.success("✅ Created Jira Issues:")
#         for k in keys:
#             st.write(f"- {k}")


# import streamlit as st
# import uuid
# from collections import defaultdict

# from ingestion.loader import load_requirements
# from ingestion.chunker import chunk_requirements
# from rag.retriever import retrieve_top_k

# from llms.epic_llm import generate_epics, regenerate_epic
# from llms.story_llm import generate_stories_from_chunk
# from llms.reducer import merge_and_dedupe

# from analysis.duplicate_detector import detect_duplicates
# from jira_integration.story_creator import create_jira_stories

# from codegen.code_generator import generate_code_for_story, SUPPORTED_STACKS


# # =========================
# # App Setup
# # =========================
# st.set_page_config(page_title="Jira AI Automation", layout="wide")
# st.title("🚀 Jira AI Automation")

# uploaded = st.file_uploader("Upload requirements (CSV / PDF / TXT)")

# # =========================
# # Load & Chunk Requirements
# # =========================
# if uploaded:
#     requirements_text = load_requirements(uploaded)
#     chunks = chunk_requirements(requirements_text)

#     st.info(f"Total chunks created: {len(chunks)}")

#     # =========================
#     # Epic Generation
#     # =========================
#     if "epics" not in st.session_state:
#         st.session_state.epics = {}

#     if st.button("🧩 Generate Epics"):
#         epic_list = generate_epics(requirements_text)

#         st.session_state.epics = {
#             f"E{idx+1}": {
#                 "epic_name": e["epic_name"],
#                 "description": e["description"],
#                 "locked": False,
#                 "jira_key": None,
#                 "stories": {}
#             }
#             for idx, e in enumerate(epic_list)
#         }

# # =========================
# # Review & Edit Epics
# # =========================
# if "epics" in st.session_state and st.session_state.epics:
#     st.subheader("🧩 Epics (Review & Refine)")

#     for epic_id, epic in st.session_state.epics.items():
#         st.markdown(f"## 🧩 Epic: {epic['epic_name']}")

#         if not epic["locked"]:
#             epic["epic_name"] = st.text_input(
#                 "Epic Name",
#                 epic["epic_name"],
#                 key=f"epic_name_{epic_id}"
#             )

#             epic["description"] = st.text_area(
#                 "Epic Description",
#                 epic["description"],
#                 height=120,
#                 key=f"epic_desc_{epic_id}"
#             )

#             col1, col2 = st.columns(2)

#             with col1:
#                 if st.button("🔄 Re-generate Epic", key=f"regen_{epic_id}"):
#                     updated = regenerate_epic(
#                         requirements_text,
#                         epic["epic_name"]
#                     )
#                     epic["epic_name"] = updated["epic_name"]
#                     epic["description"] = updated["description"]

#             with col2:
#                 if st.button("📄 Generate Stories for this Epic", key=f"stories_{epic_id}"):
#                     stories = []
#                     top_chunks = retrieve_top_k(
#                         chunks,
#                         epic["epic_name"]
#                     )

#                     for i, chunk in enumerate(top_chunks):
#                         stories.extend(
#                             generate_stories_from_chunk(chunk, i)
#                         )

#                     epic["stories"] = {
#                         f"S{idx+1}": {
#                             **story,
#                             "selected": False,
#                             "locked": False,
#                             "jira_key": None
#                         }
#                         for idx, story in enumerate(
#                             merge_and_dedupe(stories)
#                         )
#                     }

#         else:
#             st.info(f"🔒 Epic locked (Jira key: {epic['jira_key']})")

#         # =========================
#         # Story Review per Epic
#         # =========================
#         if epic["stories"]:
#             st.markdown("### 📌 Stories")

#             for story_id, story in epic["stories"].items():
#                 with st.expander(f"📄 {story['summary']}"):
#                     if not story["locked"]:
#                         story["selected"] = st.checkbox(
#                             "Select for Jira creation",
#                             value=story["selected"],
#                             key=f"sel_{epic_id}_{story_id}"
#                         )

#                         story["summary"] = st.text_input(
#                             "Summary",
#                             story["summary"],
#                             key=f"sum_{epic_id}_{story_id}"
#                         )

#                         story["description"] = st.text_area(
#                             "Description",
#                             story.get("description", ""),
#                             height=100,
#                             key=f"desc_{epic_id}_{story_id}"
#                         )

#                         st.markdown("**Acceptance Criteria**")
#                         story["acceptance_criteria"] = st.text_area(
#                             "One per line",
#                             "\n".join(story.get("acceptance_criteria", [])),
#                             key=f"ac_{epic_id}_{story_id}"
#                         ).split("\n")

#                         st.markdown("**Definition of Done**")
#                         story["definition_of_done"] = st.text_area(
#                             "One per line",
#                             "\n".join(story.get("definition_of_done", [])),
#                             key=f"dod_{epic_id}_{story_id}"
#                         ).split("\n")

#                     else:
#                         st.info(f"🔒 Story locked (Jira: {story['jira_key']})")

#             # =========================
#             # Duplicate Detection
#             # =========================
#             st.subheader("🔍 Duplicate Check")

#             duplicates_found = False
#             for story in epic["stories"].values():
#                 dups = detect_duplicates(story)
#                 if dups:
#                     duplicates_found = True
#                     st.warning(f"⚠️ Possible duplicates for {story['summary']}")
#                     for d in dups:
#                         st.write(
#                             f"- {d['jira_key']} (similarity: {d['similarity']})"
#                         )

#             force_create = True
#             if duplicates_found:
#                 force_create = st.checkbox(
#                     "I understand duplicates may exist. Create Jira issues anyway."
#                 )

#             # =========================
#             # Code Generation per Story
#             # =========================
#             st.subheader("🧠 Code Generation")

#             if "generated_code" not in st.session_state:
#                 st.session_state.generated_code = {}

#             for sid, story in epic["stories"].items():
#                 st.markdown(f"### 🧩 {story['summary']}")

#                 col1, col2 = st.columns([1, 2])

#                 with col1:
#                     stack_key = st.selectbox(
#                         "Choose Tech Stack",
#                         options=list(SUPPORTED_STACKS.keys()),
#                         format_func=lambda k: SUPPORTED_STACKS[k]["label"],
#                         key=f"stack_{epic_id}_{sid}"
#                     )

#                     if st.button("⚙️ Generate Code", key=f"code_{epic_id}_{sid}"):
#                         files = generate_code_for_story(story, stack_key)
#                         st.session_state.generated_code[(epic_id, sid)] = files

#                 if (epic_id, sid) in st.session_state.generated_code:
#                     for filename, code in st.session_state.generated_code[(epic_id, sid)].items():
#                         with st.expander(f"📄 {filename}"):
#                             st.code(code, language=filename.split(".")[-1])

#             # =========================
#             # Jira Creation (Selected Stories Only)
#             # =========================
#             if st.button("🚀 Create Selected Stories in Jira", key=f"jira_{epic_id}"):
#                 selected_stories = [
#                     s for s in epic["stories"].values()
#                     if s["selected"]
#                 ]

#                 if not selected_stories:
#                     st.warning("No stories selected.")
#                 elif not force_create:
#                     st.error("Resolve duplicates before proceeding.")
#                 else:
#                     keys = create_jira_stories(selected_stories)
#                     st.success("✅ Jira Issues Created:")
#                     for k in keys:
#                         st.write(f"- {k}")


# import streamlit as st
# from collections import defaultdict
# import uuid

# from ingestion.loader import load_requirements
# from ingestion.chunker import chunk_requirements
# from rag.retriever import retrieve_top_k

# from llms.epic_llm import generate_epics_from_chunk, regenerate_epic
# from llms.story_llm import generate_stories_from_chunk
# from llms.reducer import merge_and_dedupe
# from llms.parser import parse_llm_json

# from analysis.duplicate_detector import detect_duplicates
# from jira_integration.story_creator import create_jira_stories
# from llms.epic_pipeline import generate_epics_from_requirements
# from codegen.code_generator import generate_code_for_story, SUPPORTED_STACKS


# # =========================
# # App Setup
# # =========================
# st.set_page_config(page_title="Jira AI Automation", layout="wide")
# st.title("🚀 Jira AI Automation")

# uploaded = st.file_uploader("Upload requirements (CSV / PDF / TXT)")


# # =========================
# # Load & Chunk Requirements
# # =========================
# if uploaded:
#     requirements_text = load_requirements(uploaded)
#     raw_chunks = chunk_requirements(requirements_text)
#     chunks = [
#         {"chunk_id": f"C{idx+1}", "text": c}
#         for idx, c in enumerate(raw_chunks)
#     ]

#     st.info(f"Total chunks created: {len(chunks)}")

#     if "epics" not in st.session_state:
#         st.session_state.epics = {}

#     # =========================
#     # Epic Generation
#     # =========================
#    # =========================
# # Epic Generation (RAG)
# # =========================
# if st.button("🧩 Generate Epics"):
#     all_epics = []

#     for chunk in chunks:
#         try:
#             epics = generate_epics_from_chunk(chunk)
#             all_epics.append(epics)
#         except Exception as e:
#             st.error(str(e))

#     from llms.epic_llm import merge_and_dedupe_epics
#     final_epics = merge_and_dedupe_epics(all_epics)

#     st.session_state.epics = {
#         f"E{idx+1}": {
#             "epic_name": e["epic_name"],
#             "description": e["description"],
#             "locked": False,
#             "jira_key": None,
#             "stories": {}
#         }
#         for idx, e in enumerate(final_epics)
#     }



# # =========================
# # Review & Edit Epics
# # =========================
# if "epics" in st.session_state and st.session_state.epics:
#     st.subheader("🧩 Epics (Review & Refine)")

#     for epic_id, epic in st.session_state.epics.items():
#         st.markdown(f"## 🧩 Epic: {epic['epic_name']}")

#         if not epic["locked"]:
#             epic["epic_name"] = st.text_input(
#                 "Epic Name",
#                 epic["epic_name"],
#                 key=f"epic_name_{epic_id}"
#             )

#             epic["description"] = st.text_area(
#                 "Epic Description",
#                 epic["description"],
#                 height=120,
#                 key=f"epic_desc_{epic_id}"
#             )

#             col1, col2 = st.columns(2)

#             with col1:
#                 if st.button("🔄 Re-generate Epic", key=f"regen_{epic_id}"):
#                     raw = regenerate_epic(requirements_text, epic["epic_name"])
#                     updated = parse_llm_json(raw)
#                     epic["epic_name"] = updated["epic_name"]
#                     epic["description"] = updated["description"]

#             with col2:
#                 if st.button("📄 Generate Stories for this Epic", key=f"stories_{epic_id}"):
#                     stories = []
#                     top_chunks = retrieve_top_k(chunks, epic["epic_name"])

#                     for i, chunk in enumerate(top_chunks):
#                         stories.extend(generate_stories_from_chunk(chunk, i))

#                     merged = merge_and_dedupe(stories)

#                     epic["stories"] = {
#                         f"S{idx+1}": {
#                             **story,
#                             "selected": False,
#                             "locked": False,
#                             "jira_key": None
#                         }
#                         for idx, story in enumerate(merged)
#                     }

#         else:
#             st.info(f"🔒 Epic locked (Jira key: {epic['jira_key']})")

#         # =========================
#         # Story Review per Epic
#         # =========================
#         if epic["stories"]:
#             st.markdown("### 📌 Stories")

#             for story_id, story in epic["stories"].items():
#                 with st.expander(f"📄 {story['summary']}"):
#                     if not story["locked"]:
#                         story["selected"] = st.checkbox(
#                             "Select for Jira creation",
#                             value=story["selected"],
#                             key=f"sel_{epic_id}_{story_id}"
#                         )

#                         story["summary"] = st.text_input(
#                             "Summary",
#                             story["summary"],
#                             key=f"sum_{epic_id}_{story_id}"
#                         )

#                         story["description"] = st.text_area(
#                             "Description",
#                             story.get("description", ""),
#                             height=100,
#                             key=f"desc_{epic_id}_{story_id}"
#                         )

#                         st.markdown("**Acceptance Criteria**")
#                         story["acceptance_criteria"] = (
#                             st.text_area(
#                                 "One per line",
#                                 "\n".join(story.get("acceptance_criteria", [])),
#                                 key=f"ac_{epic_id}_{story_id}"
#                             ).split("\n")
#                         )

#                         st.markdown("**Definition of Done**")
#                         story["definition_of_done"] = (
#                             st.text_area(
#                                 "One per line",
#                                 "\n".join(story.get("definition_of_done", [])),
#                                 key=f"dod_{epic_id}_{story_id}"
#                             ).split("\n")
#                         )
#                     else:
#                         st.info(f"🔒 Story locked (Jira: {story['jira_key']})")

#             # =========================
#             # Duplicate Detection
#             # =========================
#             st.subheader("🔍 Duplicate Check")

#             duplicates_found = False
#             for story in epic["stories"].values():
#                 dups = detect_duplicates(story)
#                 if dups:
#                     duplicates_found = True
#                     st.warning(f"⚠️ Possible duplicates for {story['summary']}")
#                     for d in dups:
#                         st.write(f"- {d['jira_key']} (similarity: {d['similarity']})")

#             force_create = True
#             if duplicates_found:
#                 force_create = st.checkbox(
#                     "I understand duplicates may exist. Create Jira issues anyway.",
#                     key=f"force_{epic_id}"
#                 )

#             # =========================
#             # Code Generation per Story
#             # =========================
#             st.subheader("🧠 Code Generation")

#             if "generated_code" not in st.session_state:
#                 st.session_state.generated_code = {}

#             for sid, story in epic["stories"].items():
#                 st.markdown(f"### 🧩 {story['summary']}")

#                 col1, col2 = st.columns([1, 2])

#                 with col1:
#                     stack_key = st.selectbox(
#                         "Choose Tech Stack",
#                         options=list(SUPPORTED_STACKS.keys()),
#                         format_func=lambda k: SUPPORTED_STACKS[k]["label"],
#                         key=f"stack_{epic_id}_{sid}"
#                     )

#                     if st.button("⚙️ Generate Code", key=f"code_{epic_id}_{sid}"):
#                         files = generate_code_for_story(story, stack_key)
#                         st.session_state.generated_code[(epic_id, sid)] = files

#                 if (epic_id, sid) in st.session_state.generated_code:
#                     for filename, code in st.session_state.generated_code[(epic_id, sid)].items():
#                         with st.expander(f"📄 {filename}"):
#                             st.code(code, language=filename.split(".")[-1])

#             # =========================
#             # Jira Creation (Selected Stories Only)
#             # =========================
#             if st.button("🚀 Create Selected Stories in Jira", key=f"jira_{epic_id}"):
#                 selected_stories = [
#                     s for s in epic["stories"].values()
#                     if s["selected"]
#                 ]

#                 if not selected_stories:
#                     st.warning("No stories selected.")
#                 elif not force_create:
#                     st.error("Resolve duplicates before proceeding.")
#                 else:
#                     keys = create_jira_stories(selected_stories)
#                     st.success("✅ Jira Issues Created:")
#                     for k in keys:
#                         st.write(f"- {k}")


import streamlit as st
from collections import defaultdict

from ingestion.loader import load_requirements
from ingestion.chunker import chunk_requirements

from rag.retriever import retrieve_top_k
from llms.epic_pipeline import generate_epics_from_requirements
from llms.epic_llm import regenerate_epic

# =========================
# App Setup
# =========================
st.set_page_config(page_title="Jira AI Automation", layout="wide")
st.title("🚀 Jira AI Automation")

uploaded = st.file_uploader("Upload requirements (CSV / PDF / TXT)")

# =========================
# Load & Chunk Requirements
# =========================
if uploaded:
    requirements_text = load_requirements(uploaded)

    raw_chunks = chunk_requirements(requirements_text)
    chunks = [
        {"chunk_id": f"C{idx+1}", "text": c}
        for idx, c in enumerate(raw_chunks)
    ]

    st.info(f"Total chunks created: {len(chunks)}")

    # Init state
    if "epics" not in st.session_state:
        st.session_state.epics = {}

    if "epic_sources" not in st.session_state:
        st.session_state.epic_sources = {}

    # =========================
    # Generate Epics (RAG)
    # =========================
    if st.button("🧩 Generate Epics"):
        with st.spinner("Generating epics using RAG..."):
            final_epics = generate_epics_from_requirements(
                chunks=chunks,
                query="high level system capabilities",
                top_k=5
            )

        st.session_state.epics = {}
        st.session_state.epic_sources = {}

        for idx, epic in enumerate(final_epics):
            epic_id = f"E{idx+1}"

            st.session_state.epics[epic_id] = {
                "epic_name": epic["epic_name"],
                "description": epic["description"],
                "locked": False,
                "jira_key": None,
                "stories": {}
            }

            # store source text for regen (important!)
            st.session_state.epic_sources[epic_id] = "\n".join(
                epic.get("covered_requirements", [])
            )

# =========================
# Review & Edit Epics
# =========================
if "epics" in st.session_state and st.session_state.epics:
    st.subheader("🧩 Epics (Review & Refine)")

    for epic_id, epic in st.session_state.epics.items():
        st.markdown(f"## 🧩 Epic")

        if not epic["locked"]:
            epic["epic_name"] = st.text_input(
                "Epic Name",
                epic["epic_name"],
                key=f"name_{epic_id}"
            )

            epic["description"] = st.text_area(
                "Epic Description",
                epic["description"],
                height=140,
                key=f"desc_{epic_id}"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔄 Re-generate Epic", key=f"regen_{epic_id}"):
                    with st.spinner("Regenerating epic..."):
                        updated = regenerate_epic(
                            chunk_text=st.session_state.epic_sources.get(epic_id, ""),
                            epic_name=epic["epic_name"]
                        )

                    epic["epic_name"] = updated["epic_name"]
                    epic["description"] = updated["description"]

            with col2:
                st.button(
                    "📄 Generate Stories for this Epic",
                    key=f"stories_{epic_id}",
                    disabled=False  # wired later
                )

        else:
            st.info(f"🔒 Epic locked (Jira key: {epic['jira_key']})")
