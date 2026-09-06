# Input-to-boundary audit

This audit covers the source in this folder.

## Query boundaries

- Authentication uses the submitted email in `SELECT ... WHERE email = ?`; it is normalized with `strip().lower()` and bound as a parameter.
- Product search and category filters use `LIKE ?` and `= ?`; the search term is trimmed and capped at 80 characters. Wildcards are escaped before being placed in the parameter value.
- Product, cart, order, message, service-request, seller, and admin IDs are parsed with `parse_id`, which accepts only positive integers, then passed as SQL parameters.
- Names, descriptions, addresses, reasons, message bodies, and chatbot text are length-capped and passed as bound values. They are rendered through DOM `textContent` in the browser, not HTML interpolation.
- Sort/status/role-like fields use explicit allow-lists before SQL or state changes.

## File boundary

- Image uploads are optional and only accepted for `png`, `jpg`, `jpeg`, `webp`, or `gif`.
- The file extension is checked with `secure_filename`; the stored name is generated with `secrets.token_hex`, so client filenames cannot select a path.
- The upload directory is resolved from server configuration and created with `Path.mkdir`; `send_from_directory` serves only that directory.
- File size is limited by Flask `MAX_CONTENT_LENGTH` (5 MiB). Production should add content sniffing and malware scanning.

## Shell boundary

There are no shell commands, `subprocess` calls, `os.system` calls, or shell interpolation paths in the application. Setup commands in `README.md` are operator instructions, not runtime input paths.

## Remaining production controls

Use HTTPS, secure and HttpOnly cookies, CSRF protection for cookie-authenticated state changes, rate limits, password-reset and email verification flows, payment-provider hosted fields, UPS's authenticated API rather than the estimate, object storage scanning, audit logs, and a real authorization policy service before handling real customers.
