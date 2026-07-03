# Archaeological Audit Prompt

Audit all prior chat and list every artifact, idea, scaffold, roadmap item, config, schema, prompt, and code block that is not yet confirmed in a repo.

## Template

You are acting as a recovery agent. Your only job is to go through every single prior conversation — every message, every code block, every plan, every file draft, every scaffold, every idea, every half-built thing — and produce one master list of everything that was ever discussed, built, drafted, or planned that is NOT yet confirmed in a GitHub repo.

For each item: what it is, which project it came from, what state it is in (draft / partial / complete / unknown), and whether it should be pushed to an existing repo or a new repo.

Section 2: THINGS THAT DIED IN CHAT — discussed but never turned into any artifact, still has value.
Section 3: REPO GAPS — for each existing GitHub repo, anything discussed but never pushed.
Section 4: Push plan — repo name, branch, files to create, in order of priority.
