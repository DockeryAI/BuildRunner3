# GEO (Generative Engine Optimization) — Exhaustive Tactics Report

> Compiled March 2026 from 30+ sources. Every tactic includes its source for verification.

---

## TABLE OF CONTENTS

1. [Content Structure Tactics](#1-content-structure-tactics)
2. [Schema Markup Strategies](#2-schema-markup-strategies)
3. [Authority Building for AI Citation](#3-authority-building-for-ai-citation)
4. [Platform-Specific Optimization](#4-platform-specific-optimization)
5. [Technical SEO for AI Crawlers](#5-technical-seo-for-ai-crawlers)
6. [Brand Mention & Entity Strategies](#6-brand-mention--entity-strategies)
7. [Review Optimization](#7-review-optimization)
8. [Social Signal & Community Tactics](#8-social-signal--community-tactics)
9. [Content Freshness Strategies](#9-content-freshness-strategies)
10. [Original Research & Data Tactics](#10-original-research--data-tactics)
11. [Measurement & Monitoring](#11-measurement--monitoring)
12. [Novel / Surprising Tactics](#12-novel--surprising-tactics)
13. [GEO Algorithm Weights by Platform](#13-geo-algorithm-weights-by-platform)
14. [Key Statistics Reference](#14-key-statistics-reference)

---

## 1. CONTENT STRUCTURE TACTICS

### Answer Capsules (Strongest Single Tactic for ChatGPT Citations)

- Write a **120-150 character self-contained answer** immediately after each title or question-based H2
- 72.4% of cited blog posts included identifiable answer capsules
- Keep capsules **link-free** — 91% of cited capsules contained no links; links dilute what models perceive as standalone knowledge units
- Place links in supporting paragraphs instead
- Source: [Search Engine Land — Content Traits LLMs Quote Most](https://searchengineland.com/how-to-get-cited-by-chatgpt-the-content-traits-llms-quote-most-464868)

### Self-Contained Content Units (SCUs)

- Write passages of **60-180 words** that answer a single question completely
- AI platforms extract individual passages, not full pages — each section must function as a standalone, citable answer
- 44.2% of all LLM citations come from the first 30% of text
- Source: [Frase — Complete GEO Playbook](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook)

### BLUF (Bottom Line Up Front)

- Lead every section with the **direct answer in the first 40-60 words**, then add context
- Add TL;DR statements under key headings
- Source: [Animalz — AI Visibility Pyramid](https://www.animalz.co/blog/ai-visibility-pyramid)

### Heading Hierarchy

- Use specific H2/H3 headings that **clearly signal section topics** rather than vague labels like "Key Considerations"
- Sections averaging **120-180 words between headings** get 70% more ChatGPT citations
- Single logical H1 tag — 87% of cited pages use this structure
- 2.8x higher citation likelihood with proper H2/H3 hierarchy
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/), [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### Scannable Formatting

- Use bulleted lists, numbered lists, tables, and comparison formats
- Comparison articles lead AI citations at 32.5%
- Listicle format achieves 25% citation rate vs. 11% for opinion blogs
- 3-4 sentence paragraphs with key fact in lead sentence (43-78% visibility improvement)
- Source: [Frase](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook), [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### Fact Density

- Include statistics, data points, and specific examples **every 150-200 words**
- Content with **15+ connected entities per 1,000 words** shows 4.8x higher selection probability
- Optimal range: 15-20 entities per 1,000 words
- Include 19+ data points per article (5.4 citations vs. 2.8 without)
- Source: [Typescape — GEO Ranking Factors](https://typescape.ai/blog/geo-ranking-factors)

### Content Length

- Target minimum **1,900 words**; 2,900+ words averages 5.1 citations vs. 3.2 for sub-800 word pieces
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### Question-Based Content

- Structure headings as questions matching natural language queries
- Create FAQ sections with **8-10 well-answered questions**
- Address the "question tree" — cover subtopics and related questions, not just the main query
- Source: [Search Engine Land — 12 LLM Visibility Tactics](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)

### Multi-Modal Content

- Multi-modal content achieves **317% higher citation rates** than text-only content
- 70% of general queries on Perplexity cite visuals
- Include text + images + video + charts + structured data
- Repurpose core content across text, video, audio, and imagery
- Source: [Typescape](https://typescape.ai/blog/geo-ranking-factors), [Perplexity guides](https://www.digitalsuccess.us/blog/perplexity-seo-how-to-optimize-your-site-for-ai-powered-search-engines-in-2025.html)

---

## 2. SCHEMA MARKUP STRATEGIES

### High-Impact Schema Types (Ranked)

| Schema Type                | Impact                                              | Key Properties                                           |
| -------------------------- | --------------------------------------------------- | -------------------------------------------------------- |
| **FAQPage**                | Highest — 41% citation rate vs. 15% without         | Questions + answers matching user queries                |
| **Article/BlogPosting**    | High — required for any content targeting citations | author, datePublished, dateModified, headline, publisher |
| **HowTo**                  | High — for instructional content                    | Steps, tools, supplies                                   |
| **Product**                | High — for commerce/recommendations                 | name, description, offers, aggregateRating, pricing      |
| **Organization**           | Medium — brand entity definition                    | name, URL, logo, sameAs (social profiles), description   |
| **Person**                 | Medium — author credibility                         | name, jobTitle, worksFor, knowsAbout                     |
| **Review/AggregateRating** | Medium — social proof                               | itemReviewed, ratingValue, bestRating                    |
| **LocalBusiness**          | Medium — for local businesses                       | Use specific subtypes, include geo coordinates           |

Source: [WPRiders — 8 Schema Tactics](https://wpriders.com/schema-markup-for-ai-search-types-that-get-you-cited/)

### Schema Implementation Tactics

- Use **JSON-LD format** exclusively — the standard all major AI engines rely on
- **Attribute-rich schema** with populated pricing, ratings, and specifications outperforms generic schema by 20 percentage points
- **Strategic schema nesting** (e.g., FAQPage inside Article) increased AI citations by ~40%
- Pages with **3+ schema types** are 13% more likely to be cited
- Pages with proper schema markup are **30-40% more likely to be cited**
- Keep `dateModified` current on Article schema
- Source: [Search Engine Land — Schema Without Hype](https://searchengineland.com/schema-markup-ai-search-no-hype-472339), [Growth Marshal](https://www.growthmarshal.io/field-notes/your-generic-schema-is-useless)

### COUNTERPOINT: Schema Is Not a Silver Bullet

- SE Ranking research found FAQ schema shows **3.6 citations vs. 4.2 without** (inverse effect in some contexts)
- Schema is "a nice-to-have, not a game-changer" when authority and content quality are missing
- Over-optimizing schema while ignoring content quality reduces effectiveness
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

---

## 3. AUTHORITY BUILDING FOR AI CITATION

### Domain Authority Thresholds

- Sites with **32K+ referring domains** are 3.5x more likely to be cited by ChatGPT
- Domain Trust scores above 90 receive ~4x more citations than those below 43
- Target **190K+ monthly organic visitors** for exponential citation growth
- Pages ranked 1-45 in Google receive 60% more ChatGPT citations than those ranked 64-75
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### Authoritative List Mentions (Highest Weight Factor)

- Brands appearing in the **top 3-5 positions on high-authority list articles** are cited by ChatGPT in over 80% of relevant queries
- This is the single most influential factor across ALL chatbots:
  - ChatGPT: 41% weight
  - Perplexity: 64% weight
  - Gemini: 49% weight
- Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/)

### Earned Media & PR

- Up to **90% of citations** that drive brand visibility in LLMs come from earned media
- LLMs heavily weigh third-party sources, expert commentary, and reputable citations
- Earned media distinguishes between a brand that publishes content and one recognized by others as an authority
- Secure TechCrunch, Forbes, Search Engine Land, MarTech mentions
- Source: [Search Engine Land](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106), [Edelman](https://www.edelman.com/insights/how-brands-stay-visible-ai-search)

### E-E-A-T Optimization

- Place author bylines with **professional titles, LinkedIn profiles, and certifications** near the top
- AI search algorithms scan for trust indicators **within the first 200 words**
- Include real examples, case studies, first-hand observations
- Specify exact metrics ("conversion rates improved 47%") rather than vague claims
- Source: [Frase — GEO Playbook](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook)

### Citation Authority Flywheel

- Brands in the **top 25% for web mentions** earn 10x more AI citations than the next quartile
- Brand recognition shows **0.334 correlation** with AI citations — strongest single predictor
- Compounding effect: more citations -> more mentions -> stronger brand signals -> more citations
- Source: [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

---

## 4. PLATFORM-SPECIFIC OPTIMIZATION

### ChatGPT (61.3% Market Share)

**Algorithm Weights:**

- Authoritative list mentions: 41%
- Awards/accreditations: 18%
- Online reviews: 16%
- Customer examples/usage data: 14%
- Social sentiment: 11%

**Tactics:**

- Create comprehensive, encyclopedic guides covering topics thoroughly
- Include specific, verifiable statistics with clear attribution
- Optimize for Bing (up to 87% of SearchGPT citations match Bing's top results)
- Build Wikipedia presence — Wikipedia commands 47.9% of top-source citations
- Content with expert quotes: 4.1 citations vs. 2.4 without
- Focus on homepage clarity — clearly communicate who you serve and what you do
- FCP under 0.4s averages 6.7 citations; over 1.13s drops to 2.1

**What ChatGPT Favors:** Encyclopedic authority, established media, verified data
Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/), [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### Perplexity (3.1% Market Share)

**Algorithm Weights:**

- Authoritative list mentions: 64%
- Online reviews: 31%
- Awards/accreditations: 5%

**Tactics:**

- Prioritize recently published content (within past 12 months)
- Reddit accounts for **46.7%** of Perplexity citations — authentic subreddit participation is critical
- Target niche, specific queries over broad overviews
- Content citing multiple credible sources performs better
- New optimized content can appear in Perplexity citations **within hours**
- Create Perplexity Pages presence
- Perplexity averages 6.61 citations per response

**What Perplexity Favors:** Community-driven, recent, Reddit-heavy content
Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/), [Profound](https://www.tryprofound.com/blog/ai-platform-citation-patterns)

### Google AI Overviews

**Tactics:**

- Target **featured snippet-style formatting** with clear definitions and direct answers
- Queries with **8+ words are 7x more likely** to trigger AI Overviews
- Pages with FAQ schema are **60% more likely** to be featured
- 92.36% of AI Overview citations come from domains ranking in the top 10
- AI Overviews now appear in **50%+ of search results** reaching 1.5 billion users monthly
- Lead with 50-70 word summaries
- Structure around People Also Ask themes
- YouTube (18.8%), LinkedIn (13%), and Quora (14.3%) are significant sources

**What AI Overviews Favor:** Top-ranking content, balanced social-professional sources
Source: [Snezzi](https://snezzi.com/blog/how-to-appear-in-google-ai-overviews-a-2025-visibility-guide/), [Profound](https://www.tryprofound.com/blog/ai-platform-citation-patterns)

### Google Gemini (13.3% Market Share)

**Algorithm Weights (General):**

- Authoritative list mentions: 49%
- Google website authority: 23%
- Awards/accreditations: 15%
- Online reviews: 13%

**Algorithm Weights (Local):**

- Local business reviews: 38%
- Authoritative list mentions: 29%
- Online reviews: 19%
- GBP website authority: 14%

**Key:** Requires 3.5+ star ratings; interprets queries toward popularity
Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/)

### Claude (2.5% Market Share)

**Algorithm Weights:**

- Traditional databases & directories: 68%
- Awards/accreditations: 19%
- Customer examples/usage data: 13%

**Tactics:**

- Write with **authoritative neutrality** rather than promotional tone
- Cite sources inline and demonstrate epistemic rigor
- Use precise, specific language; avoid vague superlatives
- Focus on traditional databases: Bloomberg, Hoovers, encyclopedias, Wikipedia
- Favors established companies with longer histories
- No local recommendation capability

**What Claude Favors:** Traditional databases, directories, established companies
Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/), [Frase](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook)

---

## 5. TECHNICAL SEO FOR AI CRAWLERS

### robots.txt Configuration

Allow these AI crawler user agents:

```
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Googlebot-Extended
Allow: /
```

- **OpenAI** runs 3 bots: GPTBot (training), OAI-SearchBot (search indexing), ChatGPT-User (user-initiated)
- **Anthropic** runs 3 bots: ClaudeBot, Claude-User, Claude-SearchBot
- **Perplexity** runs 2 bots: PerplexityBot (indexing), Perplexity-User (real-time retrieval)
- Blocking the training bot does NOT block search/user bots — be granular
- Source: [ALM Corp — Anthropic Bots](https://almcorp.com/blog/anthropic-claude-bots-robots-txt-strategy/), [Paul Calvano](https://paulcalvano.com/2025-08-21-ai-bots-and-robots-txt/)

### llms.txt File

- Place at `/llms.txt` — a Markdown "table of contents" telling LLMs which pages to read first
- Format: H1 with site name (required), blockquote summary, then H2 sections with URL lists
- Also create `/llms-full.txt` with more detailed Markdown content
- **Current status:** Proposed standard only — no major AI company has officially confirmed using it
- **SE Ranking finding:** LLMs.txt showed negligible impact on ChatGPT citation likelihood; removing it actually improved accuracy
- **Verdict:** Low priority but low effort — implement if easy, don't prioritize
- Source: [Semrush — llms.txt](https://www.semrush.com/blog/llms-txt/), [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### JavaScript & Rendering

- Eliminate JavaScript dependency for critical content — AI crawlers read raw HTML only
- Content hidden behind JS interactions, dropdowns, tabs, or button clicks is invisible to AI
- Server-render or use static HTML for all content you want cited
- Source: [Omnius — GEO Practices](https://www.omnius.so/blog/best-geo-strategies)

### Core Web Vitals

- FCP under 0.4s: 6.7 average citations
- FCP over 1.13s: 2.1 average citations
- Speed Index below 1.14s performs reliably
- Fast loading signals quality; slow loading signals poor quality
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### Bing Optimization

- Up to **87% of SearchGPT/ChatGPT citations match Bing's top results**
- Use Bing Webmaster Tools alongside Google Search Console
- Ensure content ranks well in Bing, not just Google
- Source: [Omnius](https://www.omnius.so/blog/best-geo-strategies)

### Bot Accessibility Audit

- If AI bots can't access your content, they can't cite it
- Audit robots.txt, sitemap configuration, and page crawlability
- Check for accidental AI crawler blocks
- Monitor "Last Visited" timestamps for AI crawler frequency
- Source: [Conductor](https://www.conductor.com/academy/ai-citation-velocity/)

---

## 6. BRAND MENTION & ENTITY STRATEGIES

### Brand Mentions > Backlinks

- Brand mentions correlate at **0.664** vs. 0.218 for backlinks — **3x more predictive**
- Brand recognition shows 0.334 correlation with AI citations (strongest single predictor)
- Brands in top 25% for web mentions earn **10x more AI citations** than next quartile
- Source: [Typescape](https://typescape.ai/blog/geo-ranking-factors), [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### 250-Document Threshold

- An estimated **250 documents** are needed to meaningfully influence how an LLM perceives a brand
- Brands that don't publish consistently risk letting others define their narrative
- Source: [Search Engine Land](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)

### Entity Optimization

- Maintain consistent brand naming across domain, directories, and communities
- Develop detailed About pages and author bios
- Pursue Wikipedia presence where appropriate
- Actively manage knowledge panel information
- Content with 15+ connected entities per 1,000 words: 4.8x higher selection probability
- Source: [Typescape](https://typescape.ai/blog/geo-ranking-factors), [Search Engine Land GEO Guide](https://searchengineland.com/mastering-generative-engine-optimization-in-2026-full-guide-469142)

### Owned Insights / Branded Citation Hooks

- Frame common advice as branded interpretation: "Acme Analytics Tip 1: Segment your LTV cohorts by purchase channel"
- Convert generic recommendations into branded citation hooks
- Improves attribution likelihood to your organization
- Source: [Search Engine Land](https://searchengineland.com/how-to-get-cited-by-chatgpt-the-content-traits-llms-quote-most-464868)

### Homepage & Footer Optimization

- Homepage should clearly communicate who you serve and what you do
- LLMs parse homepage better than navigation menus
- Brand and service signals in footers are being picked up by LLMs
- Source: [Search Engine Land](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)

### Multi-Source Validation

- Claims appearing across **5+ external domains** improve citation rates by 67%
- Source: [Frase](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook)

---

## 7. REVIEW OPTIMIZATION

### Platform Coverage

- Claim and optimize profiles on G2, Capterra, Trustpilot, Sitejabber, Yelp, Amazon, BBB, Glassdoor
- Multi-platform review presence yields **4.6-6.3 citations** vs. 1.8 without
- Respond to reviews within 48 hours
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/), [Animalz](https://www.animalz.co/blog/ai-visibility-pyramid)

### Rating Thresholds

- Gemini requires **3.5+ star ratings** to include businesses
- Active G2 profile with recent, detailed reviews signals trust to AI engines
- Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/)

### Review Weights by Platform

- ChatGPT: Online reviews = 16% weight
- Perplexity: Online reviews = 31% weight
- Gemini General: Online reviews = 13% weight
- Gemini Local: Local reviews = 38% weight (highest single factor)
- Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/)

### Product Directories

- List on Product Hunt, AlternativeTo, Clutch with optimized information
- Maintain profiles on industry-specific directories (Gartner, IBISWorld, Bloomberg)
- Source: [Animalz](https://www.animalz.co/blog/ai-visibility-pyramid)

---

## 8. SOCIAL SIGNAL & COMMUNITY TACTICS

### Reddit (Critical for Perplexity)

- Reddit appears in **68% of AI search responses** across all platforms
- Perplexity: 46.7% of citations come from Reddit
- ChatGPT: 11.3% of top-source citations from Reddit
- Google AI Overviews: 21% of top-source citations from Reddit
- Heavy Reddit presence (6.6M+ mentions) drives 7.0 citations vs. 1.7 for minimal activity
- Reddit citations increased **450%** from March-June 2025
- **Tactic:** Find Reddit threads that AI regularly cites in your niche and add useful comments
- Focus on genuine participation, not promotional content
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/), [Profound](https://www.tryprofound.com/blog/ai-platform-citation-patterns)

### LinkedIn

- LinkedIn posts and articles can appear in AI responses within hours
- Google AI Overviews: 13% of top-source citations from LinkedIn
- Long-form articles and thought leadership posts are indexed and cited
- Source: [Search Engine Land](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)

### YouTube

- Google AI Overviews: 18.8% of citations from YouTube
- Perplexity: 13.9% of top-source citations from YouTube
- Video content with transcripts creates additional citation surfaces
- Source: [Profound](https://www.tryprofound.com/blog/ai-platform-citation-patterns)

### Quora

- Google AI Overviews: 14.3% of top-source citations from Quora
- Source: [Profound](https://www.tryprofound.com/blog/ai-platform-citation-patterns)

### Outreach to Already-Cited Content

- Find blog posts from other publishers that appear in AI responses
- Email authors asking to be included — "old-school outreach that works fast because you're piggybacking on content AI already trusts"
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### Podcast Features

- Transcripts and show notes create diverse citation sources
- Well-placed podcast appearances have ripple effects across AI indexing
- Source: [Frase](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook)

---

## 9. CONTENT FRESHNESS STRATEGIES

### Update Frequency

- **76.4%** of ChatGPT's top-cited pages were updated within the last 30 days
- Updates within 3 months: 6.0 average citations vs. 3.6 for stale content
- AI-cited content averages 1,064 days old vs. 1,432 for traditional search
- Content older than 3 months sees sharp AI citation drop-off
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/), [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### Refresh Tactics

- Quarterly refreshes with new statistics can nearly double citation chances
- Display publication dates prominently and update regularly
- Maintain "Last Updated" timestamps
- Refresh cornerstone content with updated data, new examples, and current stats
- Artificial refreshing without meaningful updates fails
- Source: [Conductor](https://www.conductor.com/academy/ai-citation-velocity/), [Search Engine Land](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)

### Perplexity Freshness

- Perplexity consistently favors content published within the past 12 months
- Because Perplexity searches in real-time, new optimized content can appear in citations within hours or days
- Source: [Frase](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook)

---

## 10. ORIGINAL RESEARCH & DATA TACTICS

### Statistics Are the #1 Optimization Technique

- Adding statistics to content improves AI visibility by **41%** — the single most effective optimization tested
- 52.2% of cited posts featured original data or branded insight
- Data-rich websites generate **4.31x more citation occurrences per URL** than directory listings
- Source: [Princeton/Georgia Tech GEO Study (KDD 2024)](https://arxiv.org/pdf/2311.09735), [Search Engine Land](https://searchengineland.com/how-to-get-cited-by-chatgpt-the-content-traits-llms-quote-most-464868)

### Three GEO Optimization Techniques (Ranked by Impact)

1. **Statistics addition** (+41% visibility improvement)
2. **Authoritative source citations** (+significant visibility gain; adding trusted citations generates 132% increase)
3. **Quotation addition** (+28% impression score improvement)

- Source: [Princeton GEO Research](https://arxiv.org/pdf/2311.09735), [Typescape](https://typescape.ai/blog/geo-ranking-factors)

### Research Content Strategy

- Layer original research for maximum citation breadth:
  - Primary report (comprehensive findings)
  - Vertical breakdowns (industry/segment-specific data)
  - Methodology pages (credibility and sub-query coverage)
  - Use-case analyses (applied contexts)
  - FAQ content (specific narrowing contexts)
- Source: [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### Proprietary Data Types That Work

- Unique survey findings
- Performance benchmarks
- Study results
- Proprietary metrics
- Frame as: "Based on our 2025 industry survey of 1,200 retailers..."
- Source: [Search Engine Land](https://searchengineland.com/how-to-get-cited-by-chatgpt-the-content-traits-llms-quote-most-464868)

### Expert Quotes

- Content with expert quotes: 4.1 citations vs. 2.4 without
- Cite named experts with credentials
- Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

---

## 11. MEASUREMENT & MONITORING

### Primary Metrics

- **Share of Model (SoM):** How often your brand appears vs. competitors in AI responses
- **Citation frequency** across tracked prompts (test 15-20 prompts across all platforms)
- **Appearance rate** (% of prompts with your citations)
- **Citation prominence** and authority positioning
- **AI-referred traffic** in GA4 from chatgpt.com, perplexity.ai, claude.ai, gemini.google.com

### Key Conversion Data

- AI-referred traffic converts at **14.2%** vs. 2.8% for Google organic (5x premium)
- AI-cited sites enjoy 4x higher conversion rates than standard organic visitors
- AI-referred sessions jumped **527%** between January-May 2025
- 1.13 billion referral visits from AI platforms (June 2025)
- Source: [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### Tools for Tracking

- **Otterly.ai** — Track ChatGPT, Perplexity, Google AIO
- **Frase AI Tracking** — Monitor across ChatGPT, Claude & more
- **OpenLens** — Free AI visibility platform (ChatGPT, Claude, Google AI, Perplexity, DeepSeek)
- **LLMrefs** — Generative AI search analytics
- **HubSpot AEO Grader** — AI search grades and competitive benchmarking
- **Ahrefs Brand Radar** — Brand mentions in AI Overviews
- **Semrush AI toolkit** — Perception tracking across generative platforms
- Source: Various tool-specific pages

### Audit Process

1. Test 15-20 prompts across ChatGPT, Perplexity, AI Overviews, and Claude
2. Document citation presence, competitors cited, brand description accuracy
3. Identify citation gaps where competitors win
4. Monitor citation sentiment and accuracy of brand descriptions
5. Track changes monthly

- Source: [Frase](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook)

### Citation Volatility Warning

- Reddit dropped from ~60% of ChatGPT citations to 10% within months (no content change)
- Only **30%** of brands maintain consistent visibility across back-to-back queries on the same platform
- Only **11%** of sites are cited by both ChatGPT and Perplexity for identical queries
- **89% of citations differ** between platforms
- Only 18% of brands appear across all three major systems
- Continuous cross-platform monitoring is essential
- Source: [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

---

## 12. NOVEL / SURPRISING TACTICS

### 1. Bing Matters More Than Google for ChatGPT

87% of SearchGPT citations match Bing's top results. Most GEO strategies ignore Bing entirely — this is a major blind spot.
Source: [Omnius](https://www.omnius.so/blog/best-geo-strategies)

### 2. FAQ Schema Can HURT Citations

SE Ranking research found FAQ schema showed 3.6 citations vs. 4.2 without — an inverse effect. Schema should supplement, not replace, quality content.
Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### 3. Keyword-Optimized URLs Perform WORSE

Low semantic relevance URLs averaged 6.4 citations vs. 2.7 for highly keyword-optimized URLs. Descriptive, natural URLs outperform keyword-stuffed alternatives.
Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### 4. LLMs.txt Has No Proven Impact

No major LLM confirmed using llms.txt files. Google explicitly rejects them. Removing llms.txt actually improved model accuracy in testing.
Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/), [Search Engine Land](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)

### 5. Footer Content Gets Picked Up

Brand and service signals placed in footers are being read by LLMs — an overlooked optimization surface.
Source: [Search Engine Land](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)

### 6. Domain Authority Barely Matters for AI

Domain Authority shows minimal correlation with AI citations: r=0.18. Traditional SEO metrics explain less than 20% of citation variance.
Source: [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### 7. 88% of AI-Cited Links Are NOT in Google's Top 10

Only 12% of AI-cited links rank in Google's top 10. There's an entire invisible citation layer that traditional SEO doesn't touch.
Source: [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### 8. Advertorials Work for AI Search

Well-placed paid editorial on reputable publishers helps brands surface in AI search, similar to earned coverage.
Source: [Search Engine Land](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)

### 9. Piggybacking on Already-Cited Content

Find content that AI currently cites and get included in it — either through Reddit comments on cited threads, or outreach to authors of cited blog posts.
Source: [SE Ranking](https://seranking.com/blog/how-to-optimize-for-chatgpt/)

### 10. Claude Barely Uses the Web

Claude relies 68% on traditional databases and directories (Bloomberg, Hoovers, encyclopedias). Web content optimization has limited impact on Claude citations compared to other platforms.
Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/)

### 11. 78% of Competitors Aren't Tracking This

78% of marketing teams lack AI visibility tracking — massive first-mover advantage for brands that start now.
Source: [ZipTie.dev](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)

### 12. Localization Is Underappreciated

AI search has moved toward localized and personalized outputs — one of the most underappreciated GEO trends for 2026.
Source: [Devenup](https://devenup.com/blog/5-key-trends-in-generative-engine-optimization)

---

## 13. GEO ALGORITHM WEIGHTS BY PLATFORM

### First Page Sage Research (11,128 queries, March 2024-December 2025)

| Factor                      | ChatGPT (61.3%) | Gemini (13.3%) | Perplexity (3.1%) | Claude (2.5%) |
| --------------------------- | --------------- | -------------- | ----------------- | ------------- |
| Authoritative list mentions | **41%**         | **49%**        | **64%**           | -             |
| Awards/accreditations       | 18%             | 15%            | 5%                | 19%           |
| Online reviews              | 16%             | 13%            | 31%               | -             |
| Customer examples/usage     | 14%             | -              | -                 | 13%           |
| Social sentiment            | 11%             | -              | -                 | -             |
| Google website authority    | -               | 23%            | -                 | -             |
| Traditional databases       | -               | -              | -                 | **68%**       |

Source: [First Page Sage](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/)

### Princeton/Georgia Tech GEO Research (Correlation Factors)

| Factor                | Correlation / Impact                          |
| --------------------- | --------------------------------------------- |
| Semantic completeness | r = 0.87 (strongest predictor)                |
| Brand mentions        | r = 0.664 (3x more predictive than backlinks) |
| Brand recognition     | r = 0.334                                     |
| Backlinks             | r = 0.218                                     |
| Domain Authority      | r = 0.18                                      |
| Statistics addition   | +41% visibility                               |
| Citation addition     | +132% visibility                              |
| Quotation addition    | +28% impression score                         |
| Authoritative tone    | +89% visibility                               |
| Multi-modal content   | +317% citation rate                           |

Source: [Princeton GEO Paper](https://arxiv.org/pdf/2311.09735), [Typescape](https://typescape.ai/blog/geo-ranking-factors)

---

## 14. KEY STATISTICS REFERENCE

| Stat                                         | Value                                          | Source             |
| -------------------------------------------- | ---------------------------------------------- | ------------------ |
| Organic CTR drop with AI Overview            | -61%                                           | Dataslayer         |
| CTR boost when brand IS cited in AI Overview | +35% vs traditional organic                    | Frase              |
| AI-referred conversion rate                  | 14.2% (vs. 2.8% organic)                       | Exposure Ninja     |
| AI-referred traffic YoY growth               | +527%                                          | Exposure Ninja     |
| AI referral visits (June 2025)               | 1.13 billion                                   | ZipTie.dev         |
| Users starting search with AI tools          | 62%                                            | Frase              |
| B2B buyers using LLMs in purchasing          | 94%                                            | Trysight           |
| AI Overviews prevalence (Feb 2026)           | 48% of all queries                             | ALM Corp           |
| AI Overview YoY increase                     | +58%                                           | ALM Corp           |
| Domains per AI response                      | 2-7 cited                                      | Frase              |
| Top 20% cited domains share                  | 80% of all references                          | Frase              |
| .com domain share of all citations           | 80.41%                                         | Profound           |
| Cross-platform citation overlap              | Only 11%                                       | ZipTie.dev         |
| Brands visible across all 3 platforms        | Only 18%                                       | ZipTie.dev         |
| Competitor inaction rate                     | 78% not tracking                               | Exposure Ninja     |
| Documents needed to influence LLM perception | 250                                            | Search Engine Land |
| Time to see citation improvements            | 4-8 weeks (structure); 3-6 months (meaningful) | Frase, Quattr      |

---

## IMPLEMENTATION PRIORITY (Quick Wins First)

### Week 1-2: Technical Foundation

- [ ] Audit robots.txt — ensure all AI crawlers are allowed
- [ ] Check if JavaScript is hiding content from crawlers
- [ ] Implement/update core schema markup (Article, Organization, FAQPage)
- [ ] Audit site speed (target FCP < 0.4s)
- [ ] Set up Bing Webmaster Tools

### Week 2-4: Content Structure

- [ ] Add answer capsules (120-150 chars) after every H2
- [ ] Restructure content into self-contained units (60-180 words each)
- [ ] Add statistics every 150-200 words
- [ ] Add expert quotes with attribution
- [ ] Add "Last Updated" timestamps to all key pages
- [ ] Update stale content with fresh data

### Month 2: Authority Building

- [ ] Audit top-performing list articles in your niche — get included
- [ ] Claim/optimize all review platform profiles
- [ ] Begin Reddit participation in relevant subreddits
- [ ] Publish on LinkedIn with thought leadership content
- [ ] Create branded frameworks and proprietary data
- [ ] Start producing original research

### Month 3+: Ongoing

- [ ] Monthly AI visibility audits across all platforms
- [ ] Quarterly content refreshes with new data
- [ ] Continued earned media and PR
- [ ] Monitor citation volatility and adapt
- [ ] Scale successful content formats
- [ ] Build toward 250-document brand presence threshold

---

## SOURCES

- [Search Engine Land — Content Traits LLMs Quote Most](https://searchengineland.com/how-to-get-cited-by-chatgpt-the-content-traits-llms-quote-most-464868)
- [Search Engine Land — 12 LLM Visibility Tactics](https://searchengineland.com/optimize-ai-search-llm-visibility-tactics-468106)
- [Search Engine Land — Mastering GEO 2026](https://searchengineland.com/mastering-generative-engine-optimization-in-2026-full-guide-469142)
- [Search Engine Land — Schema Without Hype](https://searchengineland.com/schema-markup-ai-search-no-hype-472339)
- [SE Ranking — How to Optimize for ChatGPT](https://seranking.com/blog/how-to-optimize-for-chatgpt/)
- [First Page Sage — GEO Algorithm Breakdown](https://firstpagesage.com/seo-blog/generative-engine-optimization-geo-explanation/)
- [Frase — Complete GEO Playbook](https://www.frase.io/blog/how-to-get-cited-by-ai-search-engines-the-complete-geo-playbook)
- [Frase — GEO Guide](https://www.frase.io/blog/what-is-generative-engine-optimization-geo)
- [Typescape — GEO Ranking Factors](https://typescape.ai/blog/geo-ranking-factors)
- [ZipTie.dev — Original Research Wins AI Citations](https://ziptie.dev/blog/how-original-research-wins-ai-citations/)
- [ZipTie.dev — Content Refresh Strategy](https://ziptie.dev/blog/content-refresh-strategy-for-ai-citations/)
- [Andreessen Horowitz — GEO Over SEO](https://a16z.com/geo-over-seo/)
- [Animalz — AI Visibility Pyramid](https://www.animalz.co/blog/ai-visibility-pyramid)
- [Conductor — AI Citation Velocity](https://www.conductor.com/academy/ai-citation-velocity/)
- [Princeton GEO Research Paper](https://arxiv.org/pdf/2311.09735)
- [Profound — AI Platform Citation Patterns](https://www.tryprofound.com/blog/ai-platform-citation-patterns)
- [Omnius — 6 Best GEO Practices](https://www.omnius.so/blog/best-geo-strategies)
- [WPRiders — 8 Schema Markup Tactics](https://wpriders.com/schema-markup-for-ai-search-types-that-get-you-cited/)
- [Growth Marshal — Generic Schema Fails](https://www.growthmarshal.io/field-notes/your-generic-schema-is-useless)
- [Quattr — How to Rank on ChatGPT](https://www.quattr.com/blog/how-to-rank-on-chatgpt)
- [Neil Patel — Answer Engine Optimization](https://neilpatel.com/blog/answer-engine-optimization/)
- [Surfer SEO — AEO Guide](https://surferseo.com/blog/answer-engine-optimization/)
- [HubSpot — AEO Guide](https://www.hubspot.com/products/marketing/aeo-guide)
- [Edelman — Brands in AI Search](https://www.edelman.com/insights/how-brands-stay-visible-ai-search)
- [Similarweb — GEO Guide](https://www.similarweb.com/blog/marketing/geo/what-is-geo/)
- [Semrush — GEO Guide](https://www.semrush.com/blog/generative-engine-optimization/)
- [ALM Corp — AI Overviews Surge](https://almcorp.com/blog/google-ai-overviews-surge-9-industries/)
- [Devenup — GEO Trends 2026](https://devenup.com/blog/5-key-trends-in-generative-engine-optimization)
- [WordStream — GEO vs SEO](https://www.wordstream.com/blog/generative-engine-optimization)
- [Paul Calvano — AI Bots and Robots.txt](https://paulcalvano.com/2025-08-21-ai-bots-and-robots-txt/)
- [ALM Corp — Anthropic Claude Bots](https://almcorp.com/blog/anthropic-claude-bots-robots-txt-strategy/)
