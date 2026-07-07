---
name: summer-schedule-designer
description: Designs a customized summer schedule for parents, incorporating kids' profiles (ages, hobbies, educational needs like reading/math), weather conditions, and nearby activities.
---

# Summer Schedule Designer Skill

This skill guides the agent in helping parents plan their children's summer schedules. It gathers specific profiles (ages, hobbies, interests, and educational focus areas), checks the weather forecast for their location, computes distances to local attractions, and generates an interactive HTML planner.

## Workflow

### 1. Interactive Onboarding
If any child profile or location information is missing from the parent's request, the agent **MUST** ask for clarification before running the generator. Gather the following details:
- **Location**: Home city and state (e.g., "El Sereno, Los Angeles, CA").
- **Children Profiles**: For each child:
  - Age.
  - Hobbies or interests (e.g., soccer, space, drawing, swimming).
  - Specific educational focus areas or needs (e.g., "third grader having reading difficulty", "wants to learn algebra", "needs handwriting practice").
- **Weekly Outing Day**: Ask which day of the week works best for the recurring field trip/outing (default is Friday if the parent has no preference). This maps to `--field-trip-day`.
- **Special Accommodations**: The agent **MUST** explicitly ask whether any child has sensory sensitivities, mobility limitations, or other accommodations that should shape the schedule (e.g., avoiding loud/crowded venues, needing wheelchair-accessible locations, requiring extra transition time between activities). There is no in-app filter for this — the answer must be incorporated directly into the plan: choose accommodation-appropriate attractions and activities, and call out any adjustments made in the summary in step 4.

### 2. Recommend & Confirm Activities
Before running the generator, summarize the plan for the parent and get explicit confirmation:
- State the resolved outing day and, if the location is in the Los Angeles area, name a few of the specific attractions the schedule will draw from (e.g., Griffith Observatory, Kidspace Children's Museum, Huntington Gardens); for other locations, describe the generic categories used instead (library, community pool, science museum, park).
- Summarize how each child's needs/hobbies map to specific blocks (e.g., "Reading remediation block for your 8-year-old each weekday morning", "Coding project time for your 16-year-old").
- Note how any special accommodations from step 1 are reflected (attractions swapped, extra transition time, etc.).
- Ask the parent to confirm this plan or request changes (different outing day, swap an attraction focus, adjust a child's block) before proceeding to step 3.

### 3. Formulating Custom Command
Once the plan is confirmed, execute the Python schedule builder script. The script compiles a customized dashboard tailored to these inputs.

Prefer `--profiles-file` over `--profiles`: write the profiles JSON to a temporary
file and pass its path. This sidesteps shell-quoting problems entirely (the
`--profiles` string flag remains available as a convenience for short, simple
JSON, but is more error-prone across shells).

**macOS / Linux / Windows (any shell) — preferred:**
```bash
python .agents/skills/summer-schedule-designer/scripts/generate_schedule.py \
    --location "El Sereno, Los Angeles, CA" \
    --field-trip-day Friday \
    --profiles-file /path/to/profiles.json
```
Where `profiles.json` contains an array like:
```json
[
    {"age": 8, "hobbies": ["drawing", "swimming"], "needs": ["reading-remediation"]},
    {"age": 14, "hobbies": ["soccer", "video games"], "needs": []},
    {"age": 16, "hobbies": ["coding", "volunteering"], "needs": []}
]
```

**Fallback: `--profiles` as an inline JSON string.** The correct quoting differs by shell — pick the example matching the parent's platform.

macOS / Linux (bash, zsh): wrap the JSON in single quotes; they're literal in
bash/zsh so the JSON's double quotes pass through untouched.
```bash
python .agents/skills/summer-schedule-designer/scripts/generate_schedule.py \
    --location "El Sereno, Los Angeles, CA" \
    --profiles '[{"age": 8, "hobbies": ["drawing", "swimming"], "needs": ["reading-remediation"]}, {"age": 14, "hobbies": ["soccer", "video games"], "needs": []}, {"age": 16, "hobbies": ["coding", "volunteering"], "needs": []}]'
```

Windows (PowerShell): PowerShell mangles embedded double quotes when passing
arguments to a native program like `python.exe` (quotes get silently dropped and
can cause the argument to split on spaces), even when quoted per PowerShell's own
rules. Use the `--%` stop-parsing token so PowerShell passes the rest of the line
through unmodified, and escape embedded quotes with a backslash (`\"`) instead of
PowerShell's usual `""` doubling:
```powershell
python .agents/skills/summer-schedule-designer/scripts/generate_schedule.py --% --location "El Sereno, Los Angeles, CA" --profiles "[{\"age\":8,\"hobbies\":[\"drawing\",\"swimming\"],\"needs\":[\"reading-remediation\"]},{\"age\":14,\"hobbies\":[\"soccer\",\"video games\"],\"needs\":[]},{\"age\":16,\"hobbies\":[\"coding\",\"volunteering\"],\"needs\":[]}]"
```
Note: after `--%`, PowerShell no longer expands variables or backticks on the rest
of the line, so build the full JSON literal before using this token.

**Other useful flags:**
- `--fallback-location "..."` — location to geocode instead if `--location` can't be resolved (defaults to El Sereno, Los Angeles, CA). Any geocoding or weather-fetch failure is still surfaced to the parent via a banner in the generated HTML and printed to the console — it is never silently swallowed.
- `--output /path/to/file.html` — write the planner somewhere other than `summer_schedule.html` in the workspace root.

If profile validation fails (missing `age`, wrong field types, malformed JSON), the script prints a specific error identifying which profile/field is at fault and exits non-zero — relay that message to the parent and correct the input rather than retrying blindly.

### 4. Displaying and Explaining the Schedule
After running the script, a file named `summer_schedule.html` will be generated in the root of the workspace (or at the path given to `--output`).
- Provide a summary of the generated schedule.
- Highlight the customized portions, such as weather-adapted suggestions, physical/educational balance, specific reading remediation blocks, and how they map to the kids' hobbies.
- If the parent named any special accommodations in step 1, explain how the plan accounts for them (e.g., attractions swapped out or activities adjusted).
- Provide direct printable links for worksheets and coloring pages.
- Mention the "Shuffle Week" toolbar button, which re-rolls which day gets which flexible activity (e.g., swapping which days have creative/hobby time vs. park time) without changing weather-driven or field-trip-day activities — useful if the parent wants variety without regenerating the whole plan.
- Tell the user to open `summer_schedule.html` in their web browser to interact with the planner, check distances to nearby spots, customize the entries, shuffle activities, and print the finished calendar.
