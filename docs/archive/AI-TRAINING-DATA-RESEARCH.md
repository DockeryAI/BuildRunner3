# AI Training Data Composition & Brand Citation Impact

## Research Date: March 30, 2026

---

## Executive Summary

If 54-60% of ChatGPT queries are answered from parametric knowledge (no web search), then **what's baked into the training data IS the brand landscape for the majority of AI interactions.** This research maps the entire chain: what goes into training data, how it gets weighted, which brands benefit, and what can be done about it.

---

## 1. Training Data Composition by Model

### GPT-3 (Foundation for ChatGPT)

| Dataset                      | Tokens | Weight in Training |
| ---------------------------- | ------ | ------------------ |
| Filtered Common Crawl        | 410B   | 60%                |
| WebText2 (Reddit 3+ upvotes) | 19B    | 22%                |
| Books2                       | 55B    | 8%                 |
| Books1                       | 12B    | 8%                 |
| Wikipedia                    | 3B     | 3%                 |

**Key insight:** 60% of GPT-3's training weight came from filtered Common Crawl. Wikipedia was only 3% by tokens but was **sampled 2-3x more frequently** during training due to perceived quality — effectively a 5x boost in influence.

### GPT-4 / GPT-5

OpenAI stopped publishing detailed breakdowns after GPT-3. GPT-4 was multimodal, trained on "trillions of tokens" including web text, books, code, and images. GPT-5.4 (current, March 2026) has a knowledge cutoff of August 31, 2025.

### Llama (Meta)

- Llama 3: 15+ trillion tokens from publicly available sources (7x Llama 2)
- Composition: ~50% general knowledge, ~25% math/reasoning, 5%+ non-English (30+ languages), 4x more code than Llama 2
- Meta has NOT released the training data itself — specific source breakdowns unavailable
- Uses multiple filtered versions of Common Crawl simultaneously, believing diversity improves performance

### Claude (Anthropic)

- Claude 4.6 Opus: knowledge cutoff May 2025
- Claude 4.6 Sonnet: knowledge cutoff August 2025, training data cutoff January 2026
- Anthropic does not publish training data composition
- Uses Constitutional AI approach with human + AI feedback fine-tuning
- Does not use user conversations for training unless explicitly opted in

### Key Datasets Used Across Models

| Dataset                            | Size                            | Used By                             | Description                                                  |
| ---------------------------------- | ------------------------------- | ----------------------------------- | ------------------------------------------------------------ |
| Common Crawl                       | 9.5+ PB (398 TiB uncompressed)  | 64% of analyzed LLMs                | Web crawl archive since 2008, 3-5B URLs/month                |
| C4 (Colossal Clean Crawled Corpus) | 750 GB / 38.49 TiB multilingual | Google T5, many others              | Google's filtered Common Crawl                               |
| The Pile                           | 825 GiB (260B tokens)           | EleutherAI models, many open-source | 22 diverse sub-datasets                                      |
| RefinedWeb                         | 5 trillion tokens               | Falcon, others                      | High-quality web extraction                                  |
| WebText2                           | 19B tokens                      | GPT-2, GPT-3                        | Reddit links with 3+ upvotes                                 |
| RedPajama/SlimPajama               | Varies                          | Open-source reproductions           | CC + C4 + GitHub + Books + ArXiv + Wikipedia + StackExchange |

---

## 2. Which Websites Dominate Training Data

### Common Crawl Top Domains (CC-MAIN-2026-12)

| Rank | Domain            | Pages Captured |
| ---- | ----------------- | -------------- |
| 1    | blogspot.com      | 18.6M          |
| 2    | wikipedia.org     | 3.9M           |
| 3    | wiktionary.org    | 2.0M           |
| 4    | google.com        | 1.8M           |
| 5    | wordpress.org     | 1.8M           |
| 6    | europa.eu         | 1.6M           |
| 7    | made-in-china.com | 1.1M           |
| 8    | aif.ru            | 1.0M           |
| 9    | apple.com         | 1.0M           |
| 10   | hh.ru             | 866K           |

### Washington Post C4 Analysis (15.7M websites)

Top domains by token count in Google's C4 dataset:

- **Google Patents**: 0.46% of all tokens
- **Wikipedia**: 0.19% of all tokens
- **Scribd**: 0.07%
- **New York Times**: 0.06%
- **LA Times**: ranked #6
- **The Guardian**: ranked #7
- **HuffPost**: ranked #9
- Also: half a million personal blogs (Medium, Blogspot, WordPress), plus Kickstarter, Etsy, Patreon

### What LLMs Actually Cite (Post-Training)

Analysis of 150,000+ citations across 5,000 keywords:

- **Reddit**: 40.1%
- **Wikipedia**: 26.3%
- **Google**: 23%
- **YouTube**: 23%

Platform-specific citation patterns:

- **ChatGPT**: Wikipedia dominates at 47.9% of citations
- **Perplexity**: Reddit leads at 46.7%
- **Google AI Overviews**: 93.67% cite at least one top-10 organic result

---

## 3. The Parametric vs. Retrieval Split

### The Numbers

- **54% of ChatGPT queries** are answered from parametric knowledge (no web search activated)
- **46% activate SearchGPT** (web search)
- When search IS activated: ChatGPT averages 2+ searches per query, each ~5.5 words long
- Prompts without search: average 23 words. With search: average 4.2 words.
- **ChatGPT cites Bing's top 10 results 87% of the time** when search is active

### What This Means for Brands

The majority of AI interactions draw from **frozen knowledge** — whatever was in the training data at cutoff. This creates two distinct battlefields:

1. **Parametric battlefield (54%):** Your brand's representation is locked in at training time. If you weren't prominent in the training data, you don't exist for these queries. No amount of current SEO helps.

2. **Retrieval battlefield (46%):** Traditional web presence matters — rankings, freshness, authority signals. This is where ongoing optimization pays off.

**The strategic implication:** Brands need BOTH a training-data strategy (long-term, building presence in sources that feed future model training) AND a real-time retrieval strategy (ongoing SEO/content for when models do search).

---

## 4. How Training Data Gets Weighted

### Common Crawl's Prioritization: Harmonic Centrality

Common Crawl uses **Harmonic Centrality (HC)** to decide which domains to crawl more often. HC measures how "close" a domain is to all other domains in the web's link graph.

**The chain:**

1. High HC score → more frequent crawling
2. More frequent crawling → more pages in monthly archives
3. More archive appearances → greater representation in training data
4. Greater training data representation → stronger AI model knowledge
5. Stronger model knowledge → more frequent AI citations

**Bottom line:** The domains with the lowest HC ranks (Facebook, Google, YouTube, Wikipedia) are the most crawled, have the most training data content, and show up most in AI responses.

**For smaller domains:** If your domain is in Common Crawl's long tail (rank >1M among 607M domains), this may correlate with citation difficulty regardless of content quality. Mozilla confirmed that Common Crawl's methodology **underrepresents digitally marginalized communities.**

### Wikipedia's Special Status

Wikipedia receives an intentional **5x boost** in training influence due to its open license and perceived quality. This means:

- Wikipedia articles disproportionately shape how LLMs understand entities
- A well-sourced Wikipedia page is one of the highest-leverage brand assets for AI visibility
- Wikipedia's neutral tone and citation requirements make it a "truth anchor" for LLMs

### Quality Filtering: What Gets Thrown Away

OpenAI reportedly discards **90%+ of raw web crawl data** based on:

- Quality heuristics
- Duplicate detection
- Safety filters
- Typical retention rate: 10-20% of crawled data

C4's filtering found **45% of scraped content** now explicitly restricted by websites not wanting it used for AI training.

---

## 5. Knowledge Cutoff Dates (Current as of March 2026)

| Model                 | Knowledge Cutoff | Released    |
| --------------------- | ---------------- | ----------- |
| GPT-5.4               | Aug 31, 2025     | Mar 6, 2026 |
| GPT-5.3 Instant       | Mar 3, 2026      | 2026        |
| GPT-5.2               | Dec 11, 2025     | 2025        |
| GPT-5.1               | Sep 30, 2024     | 2025        |
| GPT-5                 | Aug 7, 2025      | 2025        |
| Claude 4.6 Sonnet     | Aug 2025         | 2026        |
| Claude 4.6 Opus       | May 2025         | 2026        |
| Claude 4.5 Sonnet     | Jan 2025         | 2025        |
| Gemini 3.1 Pro        | Feb 19, 2026     | 2026        |
| Gemini 3.1 Flash Lite | Jan 2025         | Mar 2026    |
| Gemini 2.5 Flash      | Mar 25, 2025     | 2025        |
| Llama 4               | Apr 5, 2025      | 2025        |
| DeepSeek R1           | Oct 2023         | 2024        |

### Retraining Frequency

- Full retraining costs **$100M+ in compute and electricity**
- Takes weeks to months per training run
- Models are **rarely fully retrained** — companies use cheaper alternatives (fine-tuning, RAG, tool use)
- Major model updates happen roughly every **6-12 months** per provider
- Instead of retraining, companies add web browsing/search capabilities to access current information

**Implication:** Whatever is in the training data at cutoff persists for 6-12+ months before the next major model update. This is a **long feedback loop** — content published today may not enter parametric knowledge for months or years.

---

## 6. Content Licensing Deals (The Pay-to-Play Layer)

### OpenAI

| Publisher                                  | Value                              | Date     |
| ------------------------------------------ | ---------------------------------- | -------- |
| News Corp (WSJ, NY Post, etc.)             | $250M over 5 years                 | 2024     |
| Reddit                                     | ~$70M/year                         | 2024     |
| Axel Springer (Politico, Business Insider) | "Tens of millions of euros" 3-year | Dec 2023 |
| Financial Times                            | $5-10M/year                        | Apr 2024 |
| Condé Nast                                 | Multi-year, undisclosed            | 2024     |
| Hearst (20 magazines, 40+ newspapers)      | Undisclosed                        | 2024     |
| Time Magazine                              | Undisclosed                        | Jun 2024 |
| AP                                         | Undisclosed                        | Jul 2023 |
| Vox Media                                  | Undisclosed                        | 2024     |
| The Atlantic                               | Undisclosed                        | 2024     |
| Dotdash Meredith                           | Undisclosed                        | 2024     |
| Le Monde                                   | Undisclosed                        | 2024     |
| The Guardian                               | Undisclosed                        | 2025     |
| Washington Post                            | Undisclosed                        | 2025     |
| Axios (+ 4 local newsrooms funded)         | Undisclosed                        | Jan 2025 |

### Google

- Reddit: $60M/year
- ~20 national news outlets
- Associated Press (real-time news for Gemini)
- Google News Showcase partnerships

### Meta

- News Corp: up to $50M/year for 3+ years
- CNN, Fox News, People Inc., USA Today Co.
- 7+ multi-year publisher deals for Llama training

### Anthropic

- $1.5 billion copyright settlement (Sep 2025) — costliest in AI copyright history
- Donated $250K to Common Crawl

### Amazon

- New York Times: $20-25M/year
- The Athletic, Condé Nast
- Reach (usage-based compensation for Nova AI/Alexa)

### What This Means

Licensed publishers **appear frequently in AI citations** for news, finance, and business queries. Publishers WITHOUT deals **effectively become invisible in AI-mediated discovery.** Wikipedia appears in 47.9% of ChatGPT citations despite requiring no payment — its CC BY-SA license makes it the ultimate free training data.

---

## 7. Wikipedia's Outsized Influence

- Wikipedia comprises **~22% of major LLM training data** by some measures
- It receives a **5x training weight boost** over other sources
- It's the **#1 cited source in ChatGPT** at 47.9% of citations
- It's present in essentially ALL major training datasets (GPT, Llama, Claude, Gemini, etc.)

### Why Wikipedia Dominates

1. **Open license** (CC BY-SA) — no legal friction for inclusion
2. **Perceived neutrality** — models trust it as ground truth
3. **Structured format** — easy for models to extract factual claims
4. **Citation requirements** — Wikipedia articles are backed by references, creating a trust chain
5. **Entity coverage** — Wikipedia is the web's most comprehensive entity database

### Brand Implications

- A well-referenced Wikipedia page is arguably the **single highest-leverage AI visibility asset**
- Wikipedia entries shape how LLMs understand your brand's identity, category, competitors, and reputation
- Negative or absent Wikipedia coverage directly harms parametric knowledge
- Wikipedia must follow notability guidelines — you can't just create a page; the brand needs genuine third-party coverage

---

## 8. Training Data Bias Against Smaller Brands

### The Rich-Get-Richer Problem

LLMs exhibit systematic bias toward established brands:

- **Frequency bias:** Brands mentioned more often in training data develop stronger learned associations
- **Safety bias:** LLMs are trained to minimize risk — recommending a known brand (Salesforce) is "safer" than recommending an unknown startup
- **Authority bias:** Mentions in established publications (TechCrunch, Forbes, G2) carry more weight
- **Socioeconomic bias:** LLMs recommend luxury brands for high-income countries 88-100% of the time, non-luxury for low-income countries 84-98%

### Brand Search Volume as Strongest Predictor

Brand search volume (MSV) shows a **0.334 correlation** with LLM citations — the strongest predictor found. Domain rank shows 0.25 correlation. Traditional backlinks show **weak or neutral** correlation.

**Translation:** If people already search for your brand, LLMs are more likely to mention you. Brand awareness begets AI visibility in a self-reinforcing loop.

### The Consistency Problem

- Only **28% of brands** achieve both citations AND mentions in AI answers
- Only **30% of brands** stay visible across consecutive AI answers
- **40-60% of cited domains change in just one month**
- **6-27%** of mentioned brands convert to "trusted source" status

---

## 9. The Robots.txt Paradox & Opt-Out Rates

### Current Blocking Rates

- **79% of top news sites** block AI training bots
- **71%** also block AI retrieval bots
- **5.8M websites** block ClaudeBot (up from 3.2M in July 2025)
- **5.6M websites** block GPTBot (up from 3.3M in July 2025)
- **336% increase** in sites blocking AI crawlers in the past year

### The Paradox

Blocking AI crawlers **removes you from future training data AND real-time retrieval**, making your brand invisible in both parametric and search-augmented AI responses. But NOT blocking means your content trains competitors' models for free.

### Compliance Issues

**13.26% of AI bot requests ignored robots.txt** in Q2 2025 (up from 3.3% in Q4 2024). Blocking is increasingly performative rather than effective.

---

## 10. Model Collapse & Synthetic Content Contamination

### The Problem

As AI-generated content floods the web, the next generation of models inevitably ingests that synthetic content. This creates **model collapse** — models start to forget the true underlying data distribution.

### Current State

- By mid-2025, **over 10% of sources referenced by major AI tools were themselves AI-generated**
- Model collapse is happening NOW, not theoretically
- The "Virus Infection Attack" (VIA, Sep 2025) showed poisoned content can propagate through synthetic data pipelines across model generations

### Competitive Advantage of Pre-2022 Data

Companies that scraped the web BEFORE ChatGPT's November 2022 launch possess **uncontaminated human-generated data** — a resource that becomes more valuable as the web fills with synthetic content. This may **entrench incumbents** (OpenAI, Google, Meta) who captured pre-pollution data.

### Data Poisoning Risks

- Manipulating as little as **0.1% of pre-training data** can launch effective poisoning attacks
- Poisoning **1-3% of training data** significantly impairs accuracy
- Even **0.01% contamination** can substantially impact language model behavior
- "Belief manipulation" attacks can make a model prefer one product over another without requiring a trigger
- OWASP 2025 Top 10 for LLM Applications formally recognizes data/model poisoning as an integrity attack

---

## 11. Actionable Strategy: What Brands Can Do

### Tier 1: Critical (Affects 54%+ of AI queries via parametric knowledge)

1. **Wikipedia page** — Well-sourced, neutral, following notability guidelines. This is the single highest-leverage asset. Wikipedia gets 5x training weight and appears in 47.9% of ChatGPT citations.

2. **Wikidata/Knowledge Graph presence** — Structured entity data with sameAs properties linking to authoritative references. LLMs with knowledge graphs achieve 300% higher accuracy.

3. **Coverage in OpenAI/Google licensed publishers** — News Corp, FT, AP, Condé Nast, Vox Media, etc. These sources feed directly into training data through paid agreements.

4. **Consistent brand description everywhere** — Same elevator pitch, same terminology, same category framing across all properties. Inconsistency creates fragmented, weak associations.

5. **Allow AI crawlers (strategic)** — If you block GPTBot and ClaudeBot, you're invisible in both training data AND retrieval. Consider selective access.

### Tier 2: Important (Affects both parametric and retrieval)

6. **Reddit presence** — Organic engagement in relevant subreddits. Reddit appears in 40.1% of LLM citations and has $60M+ licensing deals with both Google and OpenAI. WebText2 (Reddit links with 3+ upvotes) was 22% of GPT-3's training.

7. **High-authority publication coverage** — Forbes, Bloomberg, TechCrunch, industry publications. These are crawled more frequently and weighted higher.

8. **Original research & proprietary data** — Publish unique statistics, surveys, benchmarks. Adding statistics increases AI visibility by 22%; quotations boost by 37%.

9. **Cross-platform presence** — Brands on 4+ platforms are **2.8x more likely** to appear in ChatGPT. Target: your site + Wikipedia + Reddit + 2-3 industry platforms.

10. **Content structure for AI extraction** — 40-60 word paragraphs, direct answers first, comparison tables, FAQs. Comparative listicles account for 32.5% of all AI citations.

### Tier 3: Ongoing Optimization (Affects 46% retrieval queries)

11. **Content freshness** — 65% of AI bot hits target content published within the past year. Update core content quarterly.

12. **Schema markup** — Organization, Article, FAQPage schema helps AI understand entity relationships.

13. **Brand-building over link-building** — Brand search volume (0.334 correlation) matters more than backlinks for AI visibility. Invest in brand awareness campaigns.

14. **Monthly monitoring** — Test top 25 revenue-driving prompts across ChatGPT, Perplexity, Gemini, Claude monthly. Track accuracy, sentiment, competitive positioning.

15. **Press release distribution** — Monthly insight-driven releases through high-authority wire services. Especially valuable for lesser-known brands.

### Timeline Expectations

- **Training data inclusion:** Months to years (not days/weeks like traditional SEO)
- **Content cluster results:** 60-90 days measurable impact
- **Parametric knowledge update:** 6-12 months (next major model training cycle)
- **Retrieval visibility changes:** Days to weeks (when models search the live web)

---

## 12. The Strategic Framework

```
QUERY ENTERS AI SYSTEM
         |
    +---------+
    |         |
   54%       46%
    |         |
PARAMETRIC  RETRIEVAL (RAG/Search)
    |         |
    |    Bing index, real-time web
    |    Licensed publisher feeds
    |    Current SEO matters here
    |
FROZEN KNOWLEDGE
    |
Training data from last cutoff
    |
Sources weighted by:
- Common Crawl HC rank
- Wikipedia 5x boost
- Publisher licensing deals
- Source authority/quality filtering
- Frequency of brand mentions
- Co-occurrence with category terms
```

### The Two-Speed Strategy

**Speed 1: Plant seeds for future training (6-18 month horizon)**

- Build Wikipedia/Wikidata presence
- Get covered in licensed publications
- Create a large, high-quality web footprint that Common Crawl will prioritize
- Ensure consistent brand messaging across all sources
- Publish original research that becomes reference material

**Speed 2: Win retrieval queries NOW (immediate)**

- Optimize for Bing (ChatGPT uses Bing when searching)
- Create content that answers category queries directly
- Build presence on Reddit, Forbes, Wikipedia (top cited sources)
- Structure content for AI extraction
- Monitor and respond to AI representation gaps monthly

---

## Sources

- [Washington Post: Inside the secret list of websites that make AI chatbots sound smart](https://www.washingtonpost.com/technology/interactive/2023/ai-chatbot-learning/)
- [Mozilla Foundation: Common Crawl's Impact on Generative AI](https://www.mozillafoundation.org/en/research/library/generative-ai-training-data/common-crawl/)
- [2025 AI Visibility Report: How LLMs Choose What Sources to Mention](https://thedigitalbloom.com/learn/2025-ai-citation-llm-visibility-report/)
- [AI Citations vs Mentions: Why AI Picks Competitors Over You](https://www.rankscience.com/blog/ai-citations-brand-mentions-visibility-gap)
- [How to Get Your Brand in ChatGPT's Training Data](https://www.seerinteractive.com/insights/how-to-get-your-brand-in-chatgpts-training-data)
- [Does Brand Awareness Impact LLM Visibility?](https://www.seerinteractive.com/insights/does-brand-awareness-impact-llm-visibility)
- [How LLMs Choose Brands to Recommend](https://www.trysight.ai/blog/how-llms-choose-brands-to-recommend)
- [AI Training Data Influence Strategies](https://www.trysight.ai/blog/ai-training-data-influence-strategies)
- [RAG Is the New Brand Risk](https://authoritytech.io/curated/rag-is-the-new-brand-risk)
- [Common Crawl Top 500 Domains](https://commoncrawl.github.io/cc-crawl-statistics/plots/domains)
- [Common Crawl Web Graph & AI Ranking Signals](https://commoncrawl.org/blog/how-seos-are-using-common-crawls-web-graph-data-for-ai-ranking-signals)
- [CC Rank and LLM Training Data](https://metehanai.substack.com/p/free-tool-common-crawl-llm-training)
- [LLM Knowledge Cutoff Dates](https://www.allmo.ai/articles/list-of-large-language-model-cut-off-dates)
- [How AI Licensing Deals Determine Search Visibility](https://willscott.me/2025/10/04/ai-licensing-deals-search-visibility-in-2025/)
- [Timeline of AI Publisher Deals 2024](https://digiday.com/media/2024-in-review-a-timeline-of-the-major-deals-between-publishers-and-ai-companies/)
- [Timeline of AI Publisher Deals 2025](https://digiday.com/media/a-timeline-of-the-major-deals-between-publishers-and-ai-tech-companies-in-2025/)
- [Reddit Is Winning the AI Game](https://www.cjr.org/analysis/reddit-winning-ai-licensing-deals-openai-google-gemini-answers-rsl.php)
- [Model Collapse Explained](https://www.techtarget.com/whatis/feature/Model-collapse-explained-How-synthetic-training-data-breaks-AI)
- [Model Collapse and Human-Generated Data](https://jolt.law.harvard.edu/digest/model-collapse-and-the-right-to-uncontaminated-human-generated-data)
- [Global vs Local Brand Bias in LLMs (EMNLP 2024)](https://aclanthology.org/2024.emnlp-main.707/)
- [Cognitive Biases in LLM Product Recommendations](https://arxiv.org/abs/2502.01349)
- [GPT-3 Training Data (Wikipedia)](https://en.wikipedia.org/wiki/GPT-3)
- [LLM Training Datasets Reference](https://www.glennklockwood.com/garden/LLM-training-datasets)
- [The Pile Dataset](https://pile.eleuther.ai/)
- [Llama 3 Guide](https://kili-technology.com/blog/llama-3-guide-everything-you-need-to-know-about-meta-s-new-model-and-its-data)
- [Data Poisoning: A 2026 Perspective](https://www.lakera.ai/blog/training-data-poisoning)
- [CyLab: Poisoned Datasets](https://www.cylab.cmu.edu/news/2025/06/11-poisoned-datasets-put-ai-models-at-risk-for-attack.html)
- [Publishers Blocking AI Crawlers](https://www.buzzstream.com/blog/publishers-block-ai-study/)
- [Top Sites in ChatGPT](https://www.buzzstream.com/blog/top-sites-chatgpt/)
- [LLMO White Paper](https://medium.com/@shaneht/the-llmo-white-paper-optimizing-brand-discoverability-in-models-like-chatgpt-claude-and-8fabc36f3b7e)
- [ChatGPT Search Study (Semrush)](https://www.semrush.com/blog/chatgpt-search-insights/)
- [Entity Authority in AI Search](https://searchengineland.com/entity-authority-ai-search-visibility-471619)
- [Anthropic Copyright Settlement](https://digiday.com/media/publishers-scorecard-for-big-techs-ai-licensing-deals/)
- [Content Licensing Deals Tracker](https://aiwatch.dog/licensing)
