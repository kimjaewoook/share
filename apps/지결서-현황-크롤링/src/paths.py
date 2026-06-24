# Define paths for integration with Base URL (`urllib.parse.urljoin`)

# NOTE: These paths are assumptions for the groupware document sections.
# If the actual URLs differ (e.g. `/app/approval/draft`), update the values here.
PATHS = {
    "기안문서": "/app/approval/doclist/draft/all?page=0&offset=80&property=draftedAt&direction=desc&searchtype=&keyword=&fromDate=&toDate=&duration=all",
    "결재문서": "/app/approval/doclist/approve/all?page=0&offset=80&property=draftedAt&direction=desc&searchtype=&keyword=&fromDate=&toDate=&duration=all"
}
