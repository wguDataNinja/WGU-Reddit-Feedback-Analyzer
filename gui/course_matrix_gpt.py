# course_matrix_gpt.py

import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    df_codes = pd.read_csv("data/WGU_catalog/all_course_codes.csv")
    df_matrix = pd.read_csv("data/WGU_catalog/course_year_presence_matrix.csv")
    return df_codes, df_matrix

def search_courses(df_codes, query):
    q = query.strip().lower()
    if not q:
        return pd.DataFrame(columns=df_codes.columns)
    mask_code = df_codes['CourseCode'].str.lower().str.contains(q)
    mask_name = df_codes['CourseName'].str.lower().str.contains(q)
    return df_codes[mask_code | mask_name]

def display_course_details(code, df_codes, df_matrix):
    course = df_codes[df_codes['CourseCode'] == code].iloc[0]
    matrix_row = df_matrix[df_matrix['CourseCode'] == code].iloc[0]
    st.header(course['CourseName'])
    st.subheader(f"Course Code: {course['CourseCode']}")
    st.write(f"CCN: {course['CCN']}")
    st.subheader("Presence by Year")
    years = list(range(2017, 2026))
    cols = st.columns(len(years))
    for i, year in enumerate(years):
        val = matrix_row[str(year)]
        with cols[i]:
            st.write(year)
            st.write("✅" if val == 1 else "❌")

def main():
    st.title("WGU Course Presence Explorer")

    df_codes, df_matrix = load_data()

    search_query = st.text_input("Search courses by code or name")

    # initialize session state
    if 'last_query' not in st.session_state:
        st.session_state['last_query'] = ""
    if 'selected_course' not in st.session_state:
        st.session_state['selected_course'] = None

    # reset selection if query changed
    if search_query != st.session_state['last_query']:
        st.session_state['selected_course'] = None
        st.session_state['last_query'] = search_query

    matches = search_courses(df_codes, search_query)

    selected = st.session_state['selected_course']
    if selected is None and len(matches) == 1:
        selected = matches.iloc[0]['CourseCode']

    if selected is None:
        if len(matches) > 1:
            st.subheader(f"{len(matches)} courses found:")
            for _, row in matches.iterrows():
                label = f"{row['CourseCode']} – {row['CourseName']}"
                if st.button(label, key=f"btn_{row['CourseCode']}"):
                    st.session_state['selected_course'] = row['CourseCode']
                    selected = row['CourseCode']
        elif search_query:
            st.info("No courses found. Try a different query.")
    else:
        display_course_details(selected, df_codes, df_matrix)

if __name__ == "__main__":
    main()