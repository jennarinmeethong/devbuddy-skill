# Knowledge Index

One line per knowledge entity: its id and a single-sentence summary of what it covers. This lets a reader, or an agent, find the right entity without opening files that turn out irrelevant.

Add or update a row in the same change that creates or edits the entity it describes; an index entry that drifts from its entity is worse than no index at all. `validate_knowledge.py` checks both directions: every row here must match a real entity, and every entity must have a row here.

- TYPE-A1B2C3D4: One-sentence summary of what this entity covers.
