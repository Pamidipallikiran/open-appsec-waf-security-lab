# Contributing

Thanks for helping improve this lab. Corrections, clearer documentation and tested detections are all welcome.

## Ground rules

1. **Lab only.** Do not add content that targets systems you do not own or are not authorized to test.
2. **No secrets.** Never commit tokens, passwords, keys, certificates, `.env` files or agent state.
   Use placeholders such as `YOUR_AGENT_TOKEN`.
3. **Claim only what the evidence supports.** Label every security result as one of:
   - **Verified:** a recorded test with date, event fields and Security Action
   - **Historical:** reported earlier and not re-run on the current setup
   - **Detect-only:** an event exists but the request was not blocked
   - **Not tested**

   An HTTP status code proves routing and reachability. It does not prove detection or prevention.
4. **Date your evidence** and do not present historical results as fresh tests.
5. **Keep lab-only workarounds labelled.** For example, `proxy_ssl_verify off` must carry a comment
   saying it is lab-only.

## Workflow

```bash
git checkout -b docs/short-description
# make your change
make validate
git commit -am "Describe the change"
git push -u origin docs/short-description
```

Then open a pull request. The template lists what reviewers look for. CI runs the same checks as
`make validate`, plus `docker compose config` and `nginx -t`.

## Style

- Markdown: one topic per file, relative links, fenced code blocks with a language tag.
- Shell examples: use double quotes around `curl -w` formats, for example `-w "HTTP %{http_code}\n"`.
- Keep line endings as LF and end files with a newline (see `.editorconfig`).
