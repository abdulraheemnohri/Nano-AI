# Nano AI release procedure

This repository currently declares its package version in \`pyproject.toml\`. Use that exact version for the stable Git tag, including the \`v\` prefix (for example, package version \`0.5.0\` maps to tag \`v0.5.0\`).

## Before tagging

1. Merge intended changes into \`main\` only after the pull-request checks pass.
2. Confirm the latest \`main\` push workflow is green for the exact commit to be released.
3. Review \`CHANGELOG.md\`, \`docs/A_TO_Z_AUDIT.md\`, \`docs/SECURITY.md\`, and \`docs/FINAL_RELEASE_REVIEW.md\`.
4. Run the target-machine smoke tests in the final review: install, \`nano-ai doctor\`, LiteRT-LM inference, chat, memory, authentication, model import/cancellation, scheduler recovery, backup/restore, and optional integrations actually used.
5. Verify the target machine has sufficient disk space and memory for the selected local model. Model downloads are not part of the Python package release.
6. Confirm there are no secrets, personal databases, local models, or runtime data staged for release.

## Tag and publish

After the target-machine gate is satisfied, create and push the version tag matching \`pyproject.toml\`, for example:

\`\`\`bash
git checkout main
git pull --ff-only
git status --short
git tag -a v0.5.0 -m "Nano AI v0.5.0"
git push origin v0.5.0
\`\`\`

The \`.github/workflows/release.yml\` workflow runs the test suite on Linux, Windows, and macOS; checks that the tag matches the package version; builds a wheel and source distribution; and validates them with Twine. Only after all those jobs pass does it publish a GitHub Release with the built distributions attached. A failed test or build blocks publication.

Do not use the manual workflow-dispatch option as a substitute for a release tag: dispatch validates/builds the selected tag but intentionally does not publish a release.

## After publishing

- Open the GitHub Release page and verify both distribution files are attached.
- Install the wheel in a fresh virtual environment and verify \`nano-ai --help\` and \`nano-ai doctor\`.
- Keep the full target-machine smoke-test record with the release notes.
- If any release gate fails, fix the issue, merge through normal CI, and create a new patch version/tag. Do not silently move an already published stable tag.

## Support and scope statement

Nano AI is a local-first, single-user assistant with bounded automation. The release is not a security certification or proof of unrestricted autonomous behavior. LiteRT-LM and the model must be installed separately; voice, browser, and desktop features are optional and platform-dependent. See the final release review for known limitations and required deployment safeguards.
