# AI Search User Behavior Research

## How Users Actually Behave in AI Search — Query Mechanics, Behavioral Psychology, and GEO Implications

**Research Date:** March 2026
**Sources:** 40+ studies, surveys, and datasets (2025-2026)

---

## 1. QUERY LENGTH & FORMULATION

### The Numbers

| Platform                | Avg Query Length | Format                       |
| ----------------------- | ---------------- | ---------------------------- |
| Google traditional      | 2.8-3.4 words    | Keywords, fragments          |
| Google AI Mode          | 7.2 words        | Semi-conversational          |
| ChatGPT search          | 12-23 words      | Full sentences, context-rich |
| ChatGPT general prompts | ~60 words        | Detailed, multi-constraint   |
| Perplexity              | ~15-20 words     | Research-oriented questions  |

### How Users Phrase AI Queries vs Google

**Google:** `"project management software"` (keyword lookup)
**ChatGPT:** `"best project management software for remote teams under 50 people with budget constraints"` (contextualized request with constraints)

The fundamental shift: users provide **identity, context, constraints, and desired output format** in AI queries. They're not searching -- they're briefing an advisor.

**Three tiers of prompt sophistication observed:**

1. **Casual:** `"Italy travel tips"` -- generalized, Google-like
2. **Intermediate:** Adds temporal/contextual elements (season, budget, group size)
3. **Advanced:** Includes constraints, demographics, priorities, and output format preferences

### What This Means for GEO

Content must answer the _full contextualized question_, not just the keyword. AI engines extract passages that match specific constraint combinations. Pages optimized for `"project management software"` won't surface for the 23-word query -- the content needs to address remote teams, team size, and budget explicitly.

---

## 2. MULTI-TURN CONVERSATION PATTERNS

### Session Depth Data

| Metric                             | Value              | Source                         |
| ---------------------------------- | ------------------ | ------------------------------ |
| Avg turns per ChatGPT conversation | 5.2                | LLM monitoring data            |
| Median turns                       | 2                  | Same                           |
| Single-turn conversations          | 49.4%              | Same                           |
| Multi-turn conversations           | 50.6%              | Same                           |
| Sessions with at least 1 follow-up | 73%                | Conversational search research |
| Perplexity follow-up rate          | 22-25% of sessions | Perplexity usage data          |

### The Three-Phase Conversation Pattern

Users progress through predictable stages within a single session:

1. **Broad intent discovery:** `"What are the best CRMs for small business?"`
2. **Constraint-based filtering:** `"What about ones that integrate with Gmail and are under $50/month?"`
3. **Action-oriented refinement:** `"Compare HubSpot free vs Zoho CRM for a 10-person sales team"`

Each turn deepens the system's understanding of user intent. The initial query is broad; follow-ups narrow scope or correct assumptions.

### What Triggers Follow-Up Questions

- Unsatisfying or generic initial response
- New constraints emerging mid-research ("wait, it also needs to support invoicing")
- Comparison requests after receiving a recommendation
- Price/availability/feature verification
- "What about X?" pattern -- exploring alternatives the AI didn't mention
- Drilling into a specific recommendation from a broader list

### Key Insight for GEO

73% of sessions include follow-ups, but fewer than 15% of websites optimize for predictable continuation patterns. Content that anticipates and pre-answers the obvious follow-up question has a structural advantage in AI citation.

---

## 3. INTENT DISTRIBUTION IN AI SEARCH

### The NBER/OpenAI Study (1.5M Conversations)

The most comprehensive study of actual AI usage (published Sept 2025, NBER Working Paper) classified ChatGPT interactions:

**By interaction type:**

- **Asking (49%):** Information seeking, advice, recommendations -- the advisory role
- **Doing (40%):** Task completion -- drafting, coding, planning, organizing
- **Expressing (11%):** Creative exploration, brainstorming

**By topic:**

- Practical Guidance: ~30%
- Seeking Information: ~25%
- Writing: ~25%
- Other: ~20%

### The Sixth Search Intent: Generative Intent

Traditional SEO recognizes 5 intents (informational, navigational, transactional, commercial investigation, local). AI search introduces a sixth: **generative intent** -- where users want the AI to _create something_ (a plan, a comparison, a recommendation framework) rather than find something.

### Intent Distribution Shift

The most common ChatGPT search modifiers are: "reviews," "features," "comparison," and "2025/2026" -- strongly commercial investigation. But the _way_ the intent is expressed collapses multiple funnel stages:

A single AI query like `"best CRM for my situation"` simultaneously contains:

- **Awareness** intent (what options exist)
- **Consideration** intent (how do they compare)
- **Decision** intent (which one should I pick)

The funnel didn't compress -- it collapsed into single queries.

### Work vs Personal Use

Work-related messages show steady growth, but **non-work messages have grown faster**, from 53% to over 70% of all usage. AI is becoming a life advisor, not just a work tool.

---

## 4. TRUST, VERIFICATION, AND ABANDONMENT

### The Trust Paradox

| Finding                                           | Stat            |
| ------------------------------------------------- | --------------- |
| Trust AI to guide brand decisions                 | 62%             |
| Trust AI results MORE than traditional links      | 40%             |
| Trust AI results LESS than traditional links      | 17%             |
| Don't trust AI search/summaries                   | 53%             |
| Only 8% verify AI answers themselves              | 92% don't check |
| Want better fact-checking/citations               | 50%             |
| Cross-reference AI answers via traditional search | 85%             |

**The core paradox:** Most users say they don't fully trust AI answers, yet 92% don't actually verify them. The behavioral gap between stated distrust and actual behavior is massive.

### What Builds Trust

1. **Citations and links:** Links and citations significantly increase trust _even when those citations contain errors or hallucinations_. The presence of sources = perceived credibility.
2. **Confident natural language:** Automation bias -- users accept AI outputs without question when presented confidently.
3. **Emotional connection:** Users begin viewing AI as a friend/advisor rather than a tool, which enhances perceived usefulness.
4. **Personalization:** Tailored responses feel more trustworthy than generic ones.
5. **Transparency:** AI is perceived as more transparent and credible than human experts for product recommendations.

### What Destroys Trust

- **Uncertainty displays:** When AI hedges or expresses doubt, user confidence drops
- **Inconsistent answers:** 43.4% of organizations report inaccurate/inconsistent answers as a core obstacle
- **Sensitive topics:** 57% still prefer traditional search for medical, financial, and personal topics
- **Data privacy concerns:** 90% worried about AI using data without consent
- **Platform sketchiness:** 61% have abandoned a platform due to scam/trust concerns

### The Hybrid Verification Journey

The dominant pattern: **AI first, Google second.** 85% of AI searchers cross-reference through traditional search. The journey is:

1. Ask AI for a synthesized answer
2. Accept it if it's a low-stakes query
3. Verify via Google for high-stakes decisions (purchases, health, finance)
4. Return to AI for follow-up refinement

### The Education Paradox

College-educated users show **higher** trust in AI information and greater willingness to share it -- contradicting assumptions about critical thinking correlation with skepticism.

### GEO Implication

Getting cited by AI is necessary but not sufficient. Your content also needs to rank in traditional search because 85% of users will verify there. The AI mention creates awareness; the Google result confirms credibility.

---

## 5. CLICK-THROUGH AND SOURCE ENGAGEMENT

### When AI Answers, Clicks Crater

| Metric                          | With AI Summary | Without AI Summary |
| ------------------------------- | --------------- | ------------------ |
| Click on any result             | 8%              | 15%                |
| Click within AI summary links   | 1%              | n/a                |
| Abandon session entirely        | 26%             | ~10%               |
| Zero-click (news queries, 2024) | 56%             | --                 |
| Zero-click (news queries, 2025) | 67%             | --                 |

### CTR by Position in AI Overviews

AI Overview citation CTR curves fall off a cliff -- by Position 5, citations are essentially invisible. The top 3 citation slots capture nearly all clicks.

### AI Chat Interfaces vs Traditional Search

Users click on web results **75% less often** in AI chat interfaces compared to traditional search engines. When they do click, it's overwhelmingly for:

- Transaction completion (buy, sign up, download)
- Deep technical documentation
- Verification of specific claims

### What Content Gets Cited

| Source Type                           | Citation Share                |
| ------------------------------------- | ----------------------------- |
| Wikipedia                             | ~13% of all ChatGPT citations |
| Reddit                                | ~10% (increased 87% in 2025)  |
| Community platforms (Reddit, YouTube) | 48% of all citations          |
| Third-party pages (not brand-owned)   | 85% of brand mentions         |
| URLs outside top-20 organic rankings  | 60% of AI Overview citations  |

### AI Mode Behavior (Google)

- Users spend **49 seconds** in AI Mode vs 21 seconds on AI Overviews
- **75% of AI Mode sessions end without any external click**
- Clicks in AI Mode are reserved almost exclusively for transactions
- Time by task: 77 sec comparing products, 71 sec learning, 52 sec purchasing

### Most-Cited Page Types

Blogs, videos, articles, news, and product pages (in order). Bottom-funnel content (case studies, pricing) gets the highest AI referral traffic. Top-funnel content (what-is, how-to) saw massive drops.

### GEO Implication

Don't optimize for clicks -- optimize for being the cited answer. The click happens (if at all) at the transaction layer. Your content strategy needs a **citation layer** (comprehensive, extractable content that gets pulled into AI answers) and a **conversion layer** (transactional pages that capture the 8% who do click through).

---

## 6. DESKTOP VS MOBILE: THE AI SEARCH DIVIDE

### Device Split (Referral Traffic)

| Platform      | Desktop | Mobile |
| ------------- | ------- | ------ |
| ChatGPT       | 94%     | 6%     |
| Perplexity    | 96.5%   | 3.5%   |
| Google Gemini | 91%     | 9%     |

This is a **complete reversal** of typical web usage where mobile dominates. AI search is overwhelmingly a desktop activity.

### Why Desktop Dominates

- AI search is primarily used for research and analysis requiring sustained attention
- Desktop keyboards enable the longer, more detailed queries AI benefits from
- Multi-turn conversations are friction-heavy on mobile
- Professional/productivity use cases (the primary driver) happen at desks

### Behavioral Differences by Device

**Desktop users:** Comprehensive research, detailed analysis, multi-turn conversations, sustained sessions
**Mobile users:** Quick answers, voice-first queries, discovery-oriented, single-turn interactions

### Mobile AI Behavior

- Mobile app interactions show in-app content previews first, requiring a second tap for external links
- Voice queries on mobile tend to be even more conversational but shorter
- Mobile AI use is growing but remains a fraction of desktop

### GEO Implication

AI search content optimization should be desktop-first. The user reading your AI-cited content is sitting at a computer, engaged in deep research, with multiple tabs open and high intent. Mobile optimization matters for traditional SEO but is secondary for AI citation.

---

## 7. DEMOGRAPHIC PATTERNS

### Generational Usage

| Generation          | AI Use Rate | Primary Use Case                    |
| ------------------- | ----------- | ----------------------------------- |
| Gen Z (18-24)       | 76%         | Learning, creativity, career growth |
| Millennials (25-34) | 58-68%      | Productivity, efficiency            |
| Gen X (35-54)       | 36%         | Convenience, security               |
| Boomers (55+)       | 20%         | Simple, practical tasks             |

### Behavioral Differences by Generation

**Gen Z:** Search conversationally (how they talk), use longer queries, comfortable blending platforms (TikTok, Instagram, AI), "Google first" behavior is already fading. Highest concern about job displacement despite being most digitally fluent.

**Millennials:** Most likely to view AI as a productivity engine. Pull ahead on AI-for-work use cases. 38% of Perplexity users are 25-34.

**Gen X:** Pragmatic adopters. Use AI for convenience. Less likely to experiment with prompting techniques.

**Boomers:** Prefer AI embedded in familiar interfaces. Worry most about privacy and reliability. Use keyword-style queries even in AI tools.

### Workplace AI Adoption (LSE Survey)

- Gen Z: 83%
- Millennials: 73%
- Gen X: 60%
- Boomers: 52%

### Knowledge Worker Skew

41% of Perplexity users work in knowledge-based industries (education, research, technology). Academic/research queries account for 29% of Perplexity activity.

### GEO Implication

If your audience skews younger (Gen Z/Millennial), AI search optimization is urgent -- they're already there. If your audience is Gen X/Boomer, traditional SEO remains primary but AI optimization is a growing channel. Content tone should match how the target generation phrases queries.

---

## 8. SESSION TIMING AND DURATION

### When People Use AI Search

| Pattern        | Detail                             |
| -------------- | ---------------------------------- |
| Peak hours     | 8 AM - 2 PM ET weekdays            |
| Weekend drop   | 20-50% lower than weekday          |
| Primary driver | Professional/productivity tasks    |
| Off-peak       | Evenings, early mornings, weekends |

AI search follows **office hours patterns** -- it's treated as a professional tool embedded in work routines, similar to email or spreadsheets.

### Session Duration by Platform

| Platform             | Avg Session Duration                     |
| -------------------- | ---------------------------------------- |
| ChatGPT              | 6-14.6 minutes (varies by source/period) |
| Perplexity           | 11-23 minutes                            |
| Google (traditional) | 1-2 minutes                              |
| Google AI Mode       | 49 seconds per interaction               |

### Engagement Depth

- Perplexity: 4.64 pages per visit, 16% of sessions exceed 30 minutes
- ChatGPT: 4.4 pages per visit, 10-20+ exchanges per conversation
- Google: 2-3 queries per session
- Perplexity users average 9 searches/day vs 6 daily for traditional search

### Retention and Habit Formation

- 85% of Perplexity users return after first use
- 90% revisit within 30 days
- Day 1 behavior differs from Day 100 -- strong shift toward productivity tasks over time
- Learning/research users early on are most likely to become long-term active users

### GEO Implication

Content is consumed during work hours by focused professionals. The session depth means users encounter your content in the context of a multi-query research journey, not a single search. Optimize for the _journey_, not the isolated query.

---

## 9. WHAT TRIGGERS THE SWITCH FROM GOOGLE TO AI

### The Push Factors (Why Users Leave Google)

1. **Ad clutter fatigue:** 37% overwhelmed by ads and clutter
2. **Link fatigue:** 40% tired of clicking through multiple links
3. **Information overload:** Users want one clear answer, not 10 blue links
4. **SEO spam:** Traditional search quality perceived as declining
5. **Time waste:** Multiple tabs, scanning, comparing -- the old way feels slow

### The Pull Factors (Why Users Choose AI)

1. **Instant synthesis:** 62% choose AI for summarized answers without scrolling
2. **Conversational interface:** Ask like you'd ask a person
3. **Personalization:** Context-aware responses vs generic results
4. **Follow-up capability:** Can refine without starting over
5. **One-answer clarity:** Speed, simplicity, relief from noise

### What Google Still Wins

- **Local/business queries:** Only 24% prefer AI chat for local search
- **Sensitive topics:** 57% prefer traditional search for health, finance, personal
- **Navigation:** Finding specific known websites
- **Real-time information:** Breaking news, live data
- **Trust verification:** 85% use Google to cross-check AI answers

### The Awareness Gap

Many users still don't know AI chat can function for information-seeking tasks. Once exposed, novice users quickly recognize value and plan future use. The adoption ceiling is awareness, not quality.

### GEO Implication

The queries migrating to AI first are: complex research, product comparison, how-to guidance, planning, and recommendation requests. These are high-value, high-intent queries. If your business depends on these query types, AI optimization is not optional.

---

## 10. THE PSYCHOLOGY OF AI SEARCH BEHAVIOR

### Cognitive Shifts

**From Searching to Asking:** The fundamental behavioral shift is from "looking up" to "asking." Users approach AI as an advisor, not an index. This changes the entire information architecture of how content needs to be structured.

**Executive Function Offloading:** The rise of "planning" and "routine" queries shows users offloading executive function tasks to AI. AI is no longer just answering questions -- it's structuring users' days.

**The "Good Enough" Threshold:** Users report satisfaction with direct AI answers without verifying sources, often driven by laziness rather than trust. "Good enough" responsiveness is sufficient for continued platform reliance.

**Automation Bias:** Confident AI responses in natural language trigger automatic acceptance. The presentation format (conversational, authoritative) overrides critical evaluation instincts.

**The Friend Effect:** Emotional content in AI responses causes users to view the AI as a friend rather than an assistant. This "friendship" bias enhances perceived usefulness and reduces scrutiny.

### The Dual Process

Two distinct behavioral modes emerge:

1. **Low-stakes queries:** Ask AI, accept answer, move on (no verification, no click-through)
2. **High-stakes queries:** Ask AI for synthesis, then verify via Google, read sources, compare

The threshold between these modes varies by:

- Financial impact of the decision
- Health/safety implications
- Reversibility of the action
- User's domain expertise
- Time pressure

### GEO Implication

For low-stakes queries, being the AI's cited answer IS the conversion event -- there's no click. Your brand name in the response is the exposure. For high-stakes queries, the AI mention drives the traditional search verification step, so you need to dominate both the AI answer and the organic results for the same topic.

---

## 11. CITATION INSTABILITY AND VISIBILITY

### The Volatility Problem

| Metric                                                    | Value     |
| --------------------------------------------------------- | --------- |
| Brands visible between consecutive answers                | 30%       |
| Brands visible across 5 consecutive runs                  | 20%       |
| Citations from community platforms                        | 48%       |
| Brand mentions from third-party (not owned) domains       | 85%       |
| AI Overview citations from outside top-20 organic         | 60%       |
| Pages updated < quarterly, likelihood of losing citations | 3x higher |

### What This Means

AI citation is not like ranking #1 on Google. It's probabilistic and volatile. The same query can produce different cited sources on different runs. This means:

1. You can't "set and forget" AI visibility
2. Content freshness is critical (quarterly updates minimum)
3. Third-party mentions matter more than owned content for brand visibility
4. Community presence (Reddit, forums, YouTube) drives nearly half of all citations
5. Traditional domain authority matters less -- 60% of citations come from outside the top 20

### Error Rates in AI Answers

A Choice Mutual audit found **57% error rates** in Google AI Overviews for insurance-specific queries. Yet these summaries appeared credible to general readers. The implication: AI confidently cites and synthesizes content regardless of accuracy, and users rarely check.

### GEO Implication

Brand visibility in AI requires a multi-surface strategy: owned content + Reddit/community presence + third-party mentions + regular content updates. Single-channel optimization is insufficient given citation volatility.

---

## 12. QUERY REFORMULATION BEHAVIOR

### How Users Rephrase When Unsatisfied

When AI responses don't satisfy, users employ predictable reformulation strategies:

1. **Adding specificity:** Broader query -> add constraints, demographics, context
2. **Changing frame:** If "best X" doesn't work, try "X vs Y" or "problems with X"
3. **Asking for reasoning:** "Why did you recommend X?" or "What's wrong with Y?"
4. **Narrowing scope:** Drop general query, ask about one specific aspect
5. **Progressive narrowing:** Each follow-up adds one more constraint based on the previous answer

### The Perplexity Pattern

Perplexity users demonstrate "progressively narrow or adjusting" behavior -- they refine based on received answers rather than restarting searches entirely. The session builds on itself rather than resetting.

### Expert vs Novice Reformulation

- Novices tend to rephrase with synonyms or add words randomly
- Experienced users add structural constraints (output format, audience, scope)
- The quality of reformulation directly correlates with response quality

### GEO Implication

Content needs to be rich enough to satisfy both the initial broad query AND the predictable follow-up refinements. Anticipate the narrowing chain: initial question -> constraint addition -> comparison request -> specific detail inquiry. Pages that pre-answer this chain have the best chance of persistent citation.

---

## 13. THE COLLAPSED PURCHASE FUNNEL

### Traditional Funnel vs AI Funnel

**Traditional:** Awareness (search) -> Consideration (visit sites, read reviews) -> Decision (compare, purchase)

**AI Funnel:** Single query collapses all three stages. A query like "what's the best CRM for a 10-person sales team with Gmail integration under $50/month" simultaneously discovers options, compares them, and narrows to a decision.

### The Data

- 47% of consumers have used AI to help make a purchase decision
- Consumers rely on AI for prices, comparisons, and review summaries -- the core pre-purchase steps
- 47% say AI summaries influence which brands they trust first
- 90% of B2B buyers use generative AI during the purchase journey
- AI acts as a new gatekeeper in discovery-to-purchase

### What Wins in the Collapsed Funnel

Content that simultaneously serves awareness, consideration, and decision stages. This means:

- Comprehensive comparison content > isolated product pages
- Content with pricing, features, AND recommendations
- Real user data and specific numbers > generic marketing copy
- Content that names competitors honestly > content that pretends they don't exist

### GEO Implication

The traditional content-per-funnel-stage model is obsolete for AI search. Create "decision-complete" content that takes a reader from "what is this category?" to "which specific product should I buy?" in a single page. That's what AI extracts and synthesizes.

---

## 14. CONTENT CHARACTERISTICS THAT WIN AI CITATIONS

### What Gets Extracted by AI

1. **Self-contained passages:** Paragraphs that retain meaning when read in isolation (no "as mentioned above" references)
2. **Expert quotes:** Direct quotes from industry experts receive significantly more citations
3. **Specific statistics:** Data-driven evidence enhances visibility, especially in Law, Government, and Opinion queries
4. **Structured comparisons:** Tables, lists, and frameworks that AI can easily extract and reformulate
5. **Fresh content:** Pages updated less than quarterly are 3x more likely to lose citations

### Domain Authority Still Matters (Differently)

Sites with 32K+ referring domains are 3.5x more likely to be cited by ChatGPT. But content depth, readability, and freshness matter MORE than traffic and traditional backlink metrics.

### What Content TYPES Get Cited Most

1. Blogs
2. Videos (transcripts)
3. Articles
4. News
5. Product pages

Bottom-funnel content (case studies, pricing pages) generates highest AI referral traffic. Top-funnel content (what-is, how-to) saw massive drops in AI referral value.

---

## SYNTHESIS: THE GEO BEHAVIORAL MODEL

### The User You're Optimizing For

Based on all research, the typical AI search user is:

- **Sitting at a desktop** (94%+ of AI referral traffic)
- **During work hours** (8 AM - 2 PM ET peak)
- **Typing a 12-23 word query** in natural, conversational language
- **Including specific constraints** (budget, team size, use case, timeline)
- **Expecting a synthesized answer** they won't verify for low-stakes queries
- **Planning to cross-reference via Google** for high-stakes decisions
- **Likely to ask 2-5 follow-up questions** that progressively narrow
- **Unlikely to click through** to any source (75% never leave AI interface)
- **Treating the AI as an advisor**, not a search engine
- **Collapsing the entire purchase funnel** into a single conversation

### The Content Strategy This Demands

1. **Write for extraction, not ranking.** Create self-contained passages that make sense when pulled out of context.
2. **Answer the full query chain.** Don't just answer the initial question -- pre-answer the predictable 3-4 follow-ups.
3. **Include specific data.** Numbers, comparisons, pricing, expert quotes -- the specifics AI loves to cite.
4. **Update quarterly minimum.** Stale content loses citations at 3x the rate.
5. **Build multi-surface presence.** Owned content + Reddit + YouTube + third-party mentions.
6. **Optimize for the collapsed funnel.** Decision-complete content that serves awareness through purchase.
7. **Desktop-first content design.** Your AI-referred visitor is on a computer doing deep research.
8. **Name your competitors.** Honest comparison content wins in AI synthesis over isolated product marketing.

---

## SOURCES

### Major Studies

- [OpenAI/NBER "How People Use ChatGPT" (1.5M conversations)](https://www.nber.org/papers/w34255)
- [Eight Oh Two 2026 AI & Search Behavior Study](https://eightohtwo.com/2026-ai-search-behavior-study/)
- [Orbit Media AI-Search Adoption Survey](https://www.orbitmedia.com/blog/ai-vs-google/)
- [Growth Memo AI Mode User Behavior Study (250 sessions)](https://www.growth-memo.com/p/what-our-ai-mode-user-behavior-study)
- [KPMG Trust in AI Global Study 2025](https://assets.kpmg.com/content/dam/kpmgsites/xx/pdf/2025/05/trust-attitudes-and-use-of-ai-global-report.pdf)
- [Pew Research: Americans and AI Summaries](https://www.pewresearch.org/short-reads/2025/10/01/americans-have-mixed-feelings-about-ai-summaries-in-search-results/)

### Behavioral Research

- [Nielsen Norman Group: How AI Is Changing Search Behaviors](https://www.nngroup.com/articles/ai-changing-search-behaviors/)
- [iPullRank: User Behavior in the Generative Era](https://ipullrank.com/ai-search-manual/search-behavior)
- [Washington Post: How People Use ChatGPT (47,000 conversations)](https://www.washingtonpost.com/technology/2025/11/12/how-people-use-chatgpt-data/)
- [Yext: AI Archetypes Study 2025](https://www.yext.com/about/news-media/ai-archetypes-study-2025)
- [Attest: 2025 Consumer Adoption of AI Report](https://www.askattest.com/blog/articles/2025-consumer-adoption-of-ai-report)

### Click-Through and Citation Data

- [Ahrefs: AI Overviews Reduce Clicks by 34.5%](https://ahrefs.com/blog/ai-overviews-reduce-clicks/)
- [Search Engine Land: AI Overview Citations Don't Drive Clicks](https://searchengineland.com/ai-overview-citations-clicks-what-to-do-462389)
- [Superprompt: AI Traffic Surges 527%](https://superprompt.com/blog/ai-traffic-up-527-percent-how-to-get-cited-by-chatgpt-claude-perplexity-2025)
- [Similarweb: AI Referral Traffic Winners by Industry](https://www.similarweb.com/blog/insights/ai-news/ai-referral-traffic-winners/)
- [Passionfruit: Desktop vs Mobile AI Search Traffic](https://www.getpassionfruit.com/blog/how-desktop-and-mobile-influence-ai-search-traffic-referrals)
- [Search Engine Journal: The AI Desktop/Mobile Divide](https://www.searchenginejournal.com/ai-desktop-mobile-divide-ai-search-traffic-ignores-mobile-strategy/549122/)

### Platform-Specific Data

- [Perplexity AI User Statistics 2026](https://click-vision.com/perplexity-ai-user-statistics)
- [ChatGPT Stats 2026: 800M Users](https://www.index.dev/blog/chatgpt-statistics)
- [SentiSight: Busiest Times for GenAI](https://www.sentisight.ai/the-busiest-times-for-generative-ai-usage/)

### Generational and Demographic

- [TheySaid: How Different Generations Use AI in 2026](https://www.theysaid.io/blog/how-different-generations-use-ai)
- [UC: How Every Generation Uses AI](https://www.uc.edu/news/articles/2026/01/how-every-generation-uses-ai-from-boomers-to-gen-z.html)
- [Yext: Gen Z Creates, Millennials Explore](https://www.yext.com/blog/2025/09/gen-z-millennnials-generational-search-trends-in-2025)

### GEO and Content Strategy

- [Search Engine Land: What is GEO](https://searchengineland.com/what-is-generative-engine-optimization-geo-444418)
- [GEO Academic Paper (Princeton)](https://arxiv.org/pdf/2311.09735)
- [Azoma: Sources ChatGPT Cites Most](https://www.azoma.ai/insights/the-sources-chatgpt-cites-the-most-per-query-type)
- [Azoma: 13 Promising Categories for AI Search](https://www.azoma.ai/insights/13-most-promising-categories-for-ai-search)

### Trust and Psychology

- [Inc: 92% Don't Check AI Answers](https://www.inc.com/jessica-stillman/are-you-too-trusting-of-ai-answers-92-percent-of-people-dont-check-it-for-accuracy/91209990)
- [YouGov: Most Americans Use AI But Don't Trust It](https://yougov.com/en-us/articles/53701-most-americans-use-ai-but-still-dont-trust-it)
- [Gartner: AI Search Distrusted by Half of Consumers](https://www.customerexperiencedive.com/news/ai-search-summaries-distrusted-consumers-gartner/759373/)
- [Nature: Trust in AI Progress and Challenges](https://www.nature.com/articles/s41599-024-04044-8)
- [Reuters Institute: Generative AI and News 2025](https://reutersinstitute.politics.ox.ac.uk/generative-ai-and-news-report-2025-how-people-think-about-ais-role-journalism-and-society)

### Funnel and Journey

- [Destination CRM: How AI Rewrites the Marketing Funnel](https://www.destinationcrm.com/Articles/Web-Exclusives/Viewpoints/The-New-Customer-Journey-How-AI-Search-Engines-Are-Rewriting-the-Marketing-Funnel-173679.aspx)
- [Think with Google: Customer Decision Journey and AI Search](https://business.google.com/us/think/ai-excellence/customer-decision-journey-ai-search/)
- [ArcIntermedia: Impact of AI Search on User Behavior & CTR 2026](https://www.arcintermedia.com/shoptalk/case-study-impact-of-ai-search-on-user-behavior-ctr-in-2026/)
