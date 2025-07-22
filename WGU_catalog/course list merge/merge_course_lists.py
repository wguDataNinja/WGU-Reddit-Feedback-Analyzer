# merge_courses_with_college_remap.py

import csv

# File paths
file_1 = "/data/course list merge/courses_with_college_v10.csv"
file_2 = "/data/course list merge/2025_06_course_list.csv"
output_file = "/data/course list merge/2025_06_course_list_with_college.csv"

# Mapping of old college names to newest ones (2024-04 snapshot)
college_remap = {
    "College of Business": "School of Business",
    "College of Health Professions": "Leavitt School of Health",
    "College of Information Technology": "School of Technology",
    "Teachers College": "School of Education",
    "School of Business": "School of Business",
    "Leavitt School of Health": "Leavitt School of Health",
    "School of Education": "School of Education",
    "School of Technology": "School of Technology"
}

# Load course-to-college mapping from file_1
course_college_map = {}
with open(file_1, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        code = row['CourseCode'].strip()
        raw_colleges = [c.strip() for c in row['Colleges'].split(';')]
        remapped = sorted(set(college_remap.get(c, c) for c in raw_colleges))
        course_college_map[code] = '; '.join(remapped)

# Process file_2 and generate output with cleaned Colleges column
missing = []
total = 0
found_count = 0

with open(file_2, newline='', encoding='utf-8') as f_in, \
     open(output_file, 'w', newline='', encoding='utf-8') as f_out:

    reader = csv.DictReader(f_in)
    fieldnames = reader.fieldnames + ['Colleges']
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        total += 1
        code = row['CourseCode'].strip()
        college = course_college_map.get(code)

        if not college:
            print(f"[MISSING] {code} not found in college list")
            row['Colleges'] = "NOT FOUND"
            missing.append(code)
        else:
            row['Colleges'] = college
            found_count += 1

        writer.writerow(row)

# Summary
print("\n--- Summary ---")
print(f"Total courses processed: {total}")
print(f"Found: {found_count}")
print(f"Missing: {len(missing)}")