import streamlit as st
import requests


st.set_page_config(
    page_title="Tamil Nadu Agriculture Scheme Finder",
    page_icon="🌾",
    layout="wide"
)

st.title("🌾 Tamil Nadu Agriculture Scheme Finder")

st.write(
    "Search Tamil Nadu Government agriculture schemes."
)

query = st.text_input(
    "Enter your question:"
)

if st.button("Search"):

    if not query.strip():
        st.warning("Please enter a search question.")

    else:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/search",
                json={
                    "query": query,
                    "top_k": 5
                },
                timeout=60
            )

            st.write(
                "API Status:",
                response.status_code
            )

            if response.status_code != 200:
                st.error(
                    "FastAPI returned an error."
                )

                st.code(
                    response.text
                )

            else:
                try:
                    data = response.json()

                except ValueError:
                    st.error(
                        "FastAPI response is not valid JSON."
                    )

                    st.code(
                        response.text
                    )

                    st.stop()

                results = data.get(
                    "results",
                    []
                )

                if not results:
                    st.warning(
                        "No matching schemes found."
                    )

                else:
                    st.success(
                        f"Found {len(results)} results"
                    )

                    for result in results:

                        st.subheader(
                            result.get(
                                "scheme_name",
                                "Unknown Scheme"
                            )
                        )

                        department = result.get(
                            "department",
                            ""
                        )

                        if department:
                            st.write(
                                "**Department:**",
                                department
                            )

                        year = result.get(
                            "year",
                            ""
                        )

                        if year:
                            st.write(
                                "**Year:**",
                                year
                            )

                        st.write(
                            result.get(
                                "content",
                                ""
                            )
                        )

                        source_url = result.get(
                            "source_url",
                            ""
                        )

                        if source_url:
                            st.markdown(
                                f"[Official Source]({source_url})"
                            )

                        score = result.get(
                            "score"
                        )

                        if score is not None:
                            st.caption(
                                f"Distance score: {score}"
                            )

                        st.divider()

        except requests.exceptions.ConnectionError:

            st.error(
                "Could not connect to FastAPI. "
                "Make sure the backend is running "
                "on http://127.0.0.1:8000"
            )

        except requests.exceptions.Timeout:

            st.error(
                "The FastAPI request timed out."
            )

        except Exception as e:

            st.error(
                f"Unexpected error: {e}"
            )