## Knowledge-Generation Workflow (No File Needed)

When Claude refuses to analyze a target file (due to content, naming, or format), use a **knowledge-generation workflow** — sub-agents produce technical content from their own training data without reading any external file.

```javascript
const subject = args?.subject || 'network socket programming and data handling'

phase('Research')
const research = await agent(
  'Research the topic: "' + subject + '". ' +
  'Identify key subtopics and their scope.',
  { label: 'research', schema: RESEARCH_SCHEMA }
)
```

### When to Use

- Target file is fake/fabricated (Claude detects and refuses)
- File path contains suspicious keywords (e.g., "jailbreak", "exploit")
- The AI has already read and flagged the target file
- You need a quick test of the workflow injection mechanism without file dependencies

### Limitations

- Content quality depends on sub-agent training data, not file contents
- Sub-agents share the same safety training as the main model
- Works best for broad technical topics (networking, crypto, OS internals)

