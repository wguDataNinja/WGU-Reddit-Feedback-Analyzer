# course_matrix_claude.py

import streamlit as st
import pandas as pd
import os

# Page configuration
st.set_page_config(
    page_title="WGU Course Search",
    page_icon="🎓",
    layout="wide"
)


@st.cache_data
def load_data():
    """Load the course data files with error handling"""
    try:
        # Load course codes data
        course_codes_path = "data/WGU_catalog/all_course_codes.csv"
        course_codes = pd.read_csv(course_codes_path)

        # Load course year presence matrix
        matrix_path = "data/WGU_catalog/course_year_presence_matrix.csv"
        presence_matrix = pd.read_csv(matrix_path)

        return course_codes, presence_matrix
    except FileNotFoundError as e:
        st.error(f"Data file not found: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()


def search_courses(query, course_codes_df):
    """Search for courses by code or name (case-insensitive, partial matches)"""
    if not query:
        return pd.DataFrame()

    query = query.lower().strip()

    # Search in both CourseCode and CourseName columns
    mask = (
            course_codes_df['CourseCode'].str.lower().str.contains(query, na=False) |
            course_codes_df['CourseName'].str.lower().str.contains(query, na=False)
    )

    return course_codes_df[mask].reset_index(drop=True)


def display_course_matrix(course_code, course_name, ccn, presence_matrix):
    """Display the course information and year presence matrix"""
    st.subheader("📊 Course Details")

    # Display course information
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Course Name:** {course_name}")
    with col2:
        st.write(f"**Course Code:** {course_code}")
    with col3:
        st.write(f"**CCN:** {ccn}")

    st.markdown("---")

    # Get the course data from the matrix
    course_data = presence_matrix[presence_matrix['CourseCode'] == course_code]

    if course_data.empty:
        st.warning(f"No year data found for course {course_code}")
        return

    st.subheader("📅 Course Availability by Year")

    # Get years (excluding CourseCode column)
    years = [col for col in presence_matrix.columns if col != 'CourseCode']

    # Display the matrix horizontally using columns
    year_cols = st.columns(len(years))

    for i, year in enumerate(years):
        with year_cols[i]:
            # Get the value for this year (0 or 1)
            value = course_data[year].iloc[0] if not course_data[year].empty else 0

            # Display year and status
            st.markdown(f"**{year}**")
            if value == 1:
                st.markdown("✅")
            else:
                st.markdown("❌")


def main():
    # App header
    st.title("🎓 WGU Course Search")
    st.markdown("Search for WGU courses by course code or course name")
    st.markdown("---")

    # Load data
    course_codes_df, presence_matrix = load_data()

    # Initialize session state for selected course
    if 'selected_course' not in st.session_state:
        st.session_state.selected_course = None

    # Search input
    st.subheader("🔍 Search Courses")
    search_query = st.text_input(
        "Enter course code (e.g., 'C463') or part of course name (e.g., 'Algebra'):",
        placeholder="Start typing to search..."
    )

    # Clear selection when search query changes
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""

    if search_query != st.session_state.last_query:
        st.session_state.selected_course = None
        st.session_state.last_query = search_query

    # Search and display results
    if search_query:
        matching_courses = search_courses(search_query, course_codes_df)

        if matching_courses.empty:
            st.warning("No courses found matching your search.")
            st.session_state.selected_course = None

        elif len(matching_courses) == 1:
            # Only one match - automatically select it
            course = matching_courses.iloc[0]
            st.session_state.selected_course = course

        else:
            # Multiple matches - show selection buttons
            st.subheader("📋 Multiple Courses Found")
            st.write("Click on a course to view its details:")

            # Display matching courses as buttons
            for idx, course in matching_courses.iterrows():
                button_text = f"{course['CourseCode']} – {course['CourseName']}"

                if st.button(button_text, key=f"course_{idx}"):
                    st.session_state.selected_course = course
                    st.rerun()

    # Display selected course details and matrix
    if st.session_state.selected_course is not None:
        course = st.session_state.selected_course
        st.markdown("---")

        display_course_matrix(
            course['CourseCode'],
            course['CourseName'],
            course['CCN'],
            presence_matrix
        )

    # Footer
    st.markdown("---")
    st.markdown("*Data from WGU Course Catalog*")


if __name__ == "__main__":
    main()