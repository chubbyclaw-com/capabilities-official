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

## Connecting and picking more files

When Drive is not connected yet, or the user mentions a file that is not in
`gdrive_list_files`:

1. Call `gdrive_pick_files`. It returns a link that opens Google's file picker.
2. Ask with `AskUserQuestion`, in the user's language: one `radio` question whose label
   carries the link as a Markdown link — for example
   `[Open Google Drive](<link>) and pick the files, then choose Done. The link works for 10 minutes.`
   — with two options meaning "Done" and "Cancel". Do not paste the link anywhere else.
3. When they answer Done, call `gdrive_list_files`: the files they picked are in it.
   If none of the expected files appear, ask them to confirm the picker finished and the
   confirmation page said the file was added; if it did not, offer a new link.
4. If they answered Cancel, stop and post nothing else. Do not claim a pick succeeded
   without seeing the file in `gdrive_list_files`.

The picker connects **your owner's** Google account (the person who set you up), so ask
your owner to open the link. If someone else in the group asks you to use a file you
cannot see, tell them your owner needs to pick it. Do not post the link for a group
member to open on the owner's behalf.

If a tool says Drive access was revoked or expired, do the same with a new link.

## Reading

`gdrive_read_file` returns Google Docs as Markdown, Slides as text, and Sheets as CSV of
the first sheet. For a specific part of a sheet, pass `range` (for example
`Sheet1!A1:D20`). Plain text files are downloaded.

Office files (Excel, Word, PowerPoint, and their OpenDocument versions) are read through a
Google copy: the first read creates "<name> (Google Sheets copy)" (or Docs / Slides) in the
user's Drive, and later reads reuse it, refreshed when the original changes. Mention the
copy the first time. Editing the copy does not change the original file — say so before
editing it.

Other binary files (PDF, images) come back as metadata and a link only — say so instead of
guessing their content.

## Creating

- `gdrive_create_file` with `convert_to: "doc"` turns Markdown into a Google Doc; with
  `convert_to: "sheet"` turns CSV into a Google Sheet. Without it the file is stored as-is
  (`mime_type`, or `content_base64` for binary data).
- A new spreadsheet has exactly one sheet (tab). Add the rest with `gdrive_add_sheet`
  (`file_id`, `title`, optional `values` written from A1); tab titles must be unique.
  `gdrive_update_sheet` only writes into a tab that already exists — it cannot create one.
- Prefer building spreadsheets with `gdrive_add_sheet` over uploading an `.xlsx`: binary
  uploads go through `content_base64`, which means carrying the whole file through the
  conversation, and the result is not an editable native multi-tab Sheet.
- Put new files in a picked folder with `folder_id`; otherwise they go to My Drive.
- `gdrive_create_folder` creates a folder (optionally inside a picked folder).

Share the returned link with the user.

## Editing

You may modify the files the user picked. Read the file first, change only what was asked,
and tell the user what you changed.

- Google Doc: `gdrive_edit_doc` with Docs API batchUpdate requests. Prefer
  `replaceAllText` for wording changes; it needs no character positions.
- Google Sheet: `gdrive_update_sheet` writes a 2D array into a range (formulas work).
- Other files (.txt, .csv, .md…): `gdrive_update_file` replaces the whole content.

## Moving to the trash

`gdrive_trash_file` moves a file or folder to the Drive trash; it can be restored from
there for 30 days. Before calling it, name the exact file and get the user's explicit
"yes" in chat. Never trash several files on one vague instruction.

You can never permanently delete anything — there is no tool for it. If the user wants a
file gone for good, tell them to empty it from the Drive trash themselves.

## Disconnecting

Only when the user asks: `gdrive_disconnect` forgets the Google account and the file list
(the files stay in Drive). Picking files again afterwards starts a fresh list.
