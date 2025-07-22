#fence_logic_V10.md

	1.	Extract catalog_date using extract_catalog_date().
	2.	Get valid colleges via pick_snapshot(catalog_date, COLLEGE_SNAPSHOTS).

    
	3.	Scan lines for any match in valid_colleges.
	4.	Find degree title (exclude via FILTERS["PROGRAM_TITLE_EXCLUDE_PATTERNS"]).
	5.	From degree title, scan forward to ANCHORS["CCN_HEADER"] → set start_idx.
	6.	Scan forward until next degree title, ANCHORS["SCHOOL_OF"], ANCHORS["FOOTER_TOTAL_CUS"], or ANCHORS["FOOTER_COPYRIGHT"] → set stop_idx.
	7.	Save [start_idx, stop_idx] to SECTION_INDEX_PATH.
	8.	Repeat for all degrees in the catalog.



	catalog_structure_logic_v10.md