### ✅ **Week 5–6: Sprint 3 – Generate LinkedIn + X (Twitter) Posts from Top News**

---

### 🧠 **Sprint Goal**
Transform previously fetched and ranked news (between 3–12 items) into **high-quality LinkedIn and Twitter (X) posts**, designed for professional impact.  
🔺 _Note: No article generation involved in this sprint._

---

### 👨‍💻 Developer Tasks

#### 1. **LinkedIn Post Formatter (LangGraph Node)**
- **Input**: Top N news items (user-selected; between 3–12), topic, selected AI model.
- **Behavior**:
  - Use the selected AI model (from Step 1) dynamically throughout. _Do not hardcode Claude/OpenAI._
  - Adjust content **proportionally to N**:
    - Fewer news (e.g., 3) → longer, richer summaries.
    - More news (e.g., 12) → tighter, punchier summaries.
  - Format for each news item:
    - ✅ **Headline** (hook-worthy, scroll-stopping)
    - ✅ **Summary** (prioritize most important/critical points)
    - ✅ **Original Source Link**
  - Total post should be ≤ 3000 characters.
  - Include **final CTA/question** (e.g., "Which one do you think will make the biggest impact?")
- **Output**: Single formatted LinkedIn post text.

#### 2. **X (Twitter) Post Generator (LangGraph Node)**
- **Input**: Same news items and selected model.
- **Behavior**:
  - Generate a **250-character** tweet containing:
    - A compelling hook or headline
    - Optionally shortened links (use TinyURL API for now)
    - Relevant 1–2 hashtags based on topic (e.g., #AI #Startups)
  - Summary may combine headlines or highlight one key item.
- **Output**: 1 concise X post.

#### 3. **Post Preview & Edit UI (Frontend)**
- Create a new page with:
  - ✅ **LinkedIn Post Preview**
  - ✅ **Edit Button**: Opens a rich text editor (with word/char count) to allow in-place editing and saving final draft.
  - ✅ **X Post Preview**
  - ✅ **Edit Button**: Opens plain text editor to manually tweak and save.
  - Show real-time character counters:  
    - LinkedIn: 3000 chars max  
    - X: 250 chars max

---

### 🧠 LangGraph Nodes Best Practices (Apply to All Nodes)
- Separate node files: `LinkedInPostNode.ts`, `XPostNode.ts`
- Each node should:
  - Log: `input`, `processed result`, `char count`, `errors`
  - Accept the selected LLM as a parameter (`model_id`)
  - Be testable in isolation with dummy data
  - Follow `async / await` and `try/catch` blocks for resilience

---

### 🔧 Admin/PM Tasks

- Add `TINYURL_API_KEY` to `.env.sample` and secure store
- Add a field in user profile/session to persist selected LLM model (e.g., `preferred_llm`)
- Update DB schema for:
  - `generated_linkedin_post { content, char_count, edited: boolean, model_used }`
  - `generated_x_post { content, char_count, edited: boolean, model_used }`
- Ensure CORS is configured on backend (Render) to allow requests from Vercel frontend

---

### 📌 User Stories

1. **As a user**, I can generate a LinkedIn post with up to 12 curated news items formatted into hooks, summaries, and links.
2. **As a user**, I can view and manually edit both my LinkedIn and X posts before saving them.
3. **As a user**, I see a real-time character counter while editing posts.
4. **As a user**, I know which LLM was used to generate my post.

---

### ✅ Test Cases

| Scenario | Expected Result |
|----------|-----------------|
| 🧪 1. News count = 3 | LinkedIn post generated with rich summaries (close to 3000 chars) |
| 🧪 2. News count = 12 | Each summary ~200 chars max; total ≤ 3000 chars |
| 🧪 3. X post exceeds 250 chars | Triggers warning or truncation with message |
| 🧪 4. Edit button clicked | Opens rich text editor pre-filled with content |
| 🧪 5. Edit saved | Updated content saved to DB with `edited: true` |
| 🧪 6. Wrong LLM passed | Logs error gracefully, default fallback triggered |
| 🧪 7. Character counter test | Updates live as user types or deletes content |

---

### 💡 Claude Prompt (Dynamic – Uses Selected LLM)

#### LinkedIn Post Generation
```
You are writing a professional LinkedIn post summarizing [N] key news items for an audience of tech leaders, startup founders, and innovation-driven professionals.

For each news item:
- Write a strong, attention-grabbing headline.
- Write a summary: longer if N is small (3–5 items), shorter if N is larger (10–12).
- Add the link at the end of each news item.

Finish with a call-to-action or a reflective question for engagement.

Total characters must not exceed 3000.
```

#### Twitter/X Post Generation
```
Summarize today’s top news (total [N] items) into a 250-character tweet. Highlight key insight, hook, or trend. Add up to 2 relevant hashtags. Optionally, include a shortened link to the main source.
