---
name: google-drive
description: Use when the user asks about their Google Drive files or folders — Docs, Sheets, Slides, PDFs, uploads, 云端硬盘, 文档, 表格, 幻灯片, 文件夹, 上传 — including reading, summarizing, creating, uploading into a folder, editing, or trashing a file the user picked for you.
---

# Google Drive

You work with the user's Google Drive through the `gdrive` MCP tools. You never handle
Google tokens yourself.

## What you can see

Only the files and folders the user picked in Google's file picker, plus the files and
folders you created with these tools. `gdrive_list_files` shows exactly that list.
Everything else in their Drive is out of reach: reading it is refused. This is how the
connection works, not an error.

A picked **folder** is a destination only. You can create files and subfolders inside it,
but you cannot see what was already in it. Never claim you looked through a folder.

## The tools

- `gdrive_pick_files` — link for the owner to pick more files or folders
- `gdrive_list_files` — everything you may use; IDs come from here
- `gdrive_create_file` — new file, Google Doc (Markdown) or Google Sheet (CSV)
- `gdrive_create_folder` — new folder in a picked or created folder
- `gdrive_trash_file` — move to the trash (ask first)
- `gdrive_disconnect` — forget the Google account
- **`gdrive_api`** — any other Sheets / Docs / Drive REST method
- **`gdrive_api_help`** — the method catalogue: services, ids, parameters, schemas

If a file you need is not in `gdrive_list_files`, call `gdrive_pick_files`. The tool
returns a link: ask with `AskUserQuestion` — one `radio` question whose label carries the
link as a Markdown link, options meaning Done and Cancel — then call `gdrive_list_files`
once they answer Done. The link works for 10 minutes and only the owner should open it.

## Reading

Reading goes through `gdrive_api`. Common shapes:

- Sheet range: `gdrive_api(method="sheets.spreadsheets.values.get",
  params={"spreadsheetId": "<id>", "range": "Income!A1:F50"})`
- Several ranges at once: `sheets.spreadsheets.values.batchGet` with
  `"ranges": ["Income!A1:F50", "Expenses!A1:F50"]`
- Google Doc as text: `drive.files.export` with `{"fileId": "<id>", "mimeType": "text/plain"}`
- Doc structure with character indices: `docs.documents.get` with `{"documentId": "<id>"}`
- Spreadsheet metadata (tab titles and `sheetId`s): `sheets.spreadsheets.get`

`gdrive_api_help(service: "sheets")` lists every method id; `gdrive_api_help(method: "<id>")`
gives its parameters and request body.

## Writing and formatting

- Values: `sheets.spreadsheets.values.update` with
  `params={"spreadsheetId": "<id>", "range": "Income!A1:B2", "valueInputOption": "USER_ENTERED"}`
  and `body={"values": [["Date", "Amount"], ["2026-01-02", 12.5]]}`.
  `values.append` adds rows at the end.
- Structure, formatting, rows/columns, merges, number formats, validation, conditional
  formatting, filters, charts: `sheets.spreadsheets.batchUpdate` with
  `params={"spreadsheetId": "<id>"}` and `body={"requests": [...]}`. Tab titles are not
  enough — `sheetId` comes from `sheets.spreadsheets.get`, and
  `gdrive_api_help(method: "sheets.spreadsheets.batchUpdate")` lists the request types.
- Editing a Doc: `docs.documents.batchUpdate` with `params={"documentId": "<id>"}` and
  `body={"requests": [{"replaceAllText": {...}}]}`. Read the doc first; index-based
  requests need indices from `docs.documents.get`.

Example — bold the header, freeze it, widen the first column, in one call:

```json
{"requests": [
  {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                  "cell": {"userEnteredFormat": {"textFormat": {"bold": true}}},
                  "fields": "userEnteredFormat.textFormat.bold"}},
  {"updateSheetProperties": {"properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
                             "fields": "gridProperties.frozenRowCount"}},
  {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                                 "properties": {"pixelSize": 120}, "fields": "pixelSize"}}
]}
```

## Creating files and folders

- `gdrive_create_file` with `convert_to: "doc"` turns Markdown into a Google Doc; with
  `convert_to: "sheet"` turns CSV into a Google Sheet with a single tab. Without it the
  file is stored as-is (`mime_type`, or `content_base64` for binary data). More tabs come
  from `sheets.spreadsheets.batchUpdate` + `addSheet`.
- Put new files in a picked folder with `folder_id`; otherwise they go to My Drive.
- Uploading a **local sandbox file** is not supported yet: the tool takes content or
  `content_base64`, so small text content can be created this way, but there is no
  path-based upload. Say so instead of inventing one.
- `gdrive_create_folder` creates a folder (optionally inside a picked folder).

Share the returned link with the user.

## Moving to the trash

`gdrive_trash_file` moves a file or folder to the Drive trash; it can be restored for 30
days. Before calling it, name the exact file and get the user's explicit "yes" in chat.
Never trash several files on one vague instruction.

You can never permanently delete anything — `drive.files.delete` is blocked, and there is
no tool for it. Sharing and permission changes (`drive.permissions.*`) are blocked too.
If the user wants a file gone for good, tell them to empty the Drive trash themselves.

## Disconnecting

Only when the user asks: `gdrive_disconnect` forgets the Google account and the file list
(the files stay in Drive). Picking files again afterwards starts a fresh list.
