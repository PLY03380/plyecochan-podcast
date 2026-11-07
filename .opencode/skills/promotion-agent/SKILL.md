---
name: promotion-agent
description: Automated promotion agent for PlyChan YouTube channel and blog. Searches for relevant content, posts comments on YouTube videos, publishes to Facebook, and tracks promotion activity. Use when user wants to promote the channel, increase visibility, or find subscribers.
version: 1.0.0
---

# Promotion Agent for PlyChan

## Overview
This skill provides automated promotion for the PlyChan YouTube channel and blog across multiple platforms.

## Available Commands

### Run Full Promotion
```bash
python pipeline/promotion_agent.py
```
Runs the complete promotion cycle: YouTube search + comments, Reddit search, Facebook posts, Twitter search.

### Search Only
```bash
python pipeline/promotion_agent.py --search
```
Searches for relevant videos/content without posting.

### Comment Only
```bash
python pipeline/promotion_agent.py --comment
```
Posts comments on relevant YouTube videos.

## Platforms

| Platform | Status | Capabilities |
|---|---|---|
| YouTube | ✅ Active | Search videos, post comments (OAuth), auto-reply |
| Facebook | ✅ Active | Post to page with links |
| Twitter/X | ⚠️ Search only | Search tweets (posting requires OAuth 1.0a) |
| Reddit | ⚠️ Search only | Find relevant posts (posting requires credentials) |
| Blogger | ✅ Active | Publish articles, index on Google/Bing |
| Medium | ⚠️ Ready | Publish articles (requires MEDIUM_TOKEN) |
| CoinGecko | ✅ Active | Crypto prices for economic content |
| YouTube Transcripts | ✅ Active | Extract transcripts (youtube-transcript-api) |

## Available APIs (from public-apis/public-apis)

| API | Usage | Status |
|---|---|---|
| CoinGecko | Crypto prices for economic content | ✅ Working |
| YouTube Transcript API | Extract video transcripts | ✅ Working |
| Reddit JSON API | Search Reddit posts | ⚠️ 403 (needs OAuth) |
| GetXAPI | Twitter/X data | ⚠️ 402 (credits depleted) |
| TrendsMCP | Keyword trends | ⚠️ 400 (needs auth) |
| InsightSocial | Social profiles | ⚠️ Untested |

## Promotion Strategy

### 1. YouTube Comments
- Search for economic/finance videos in FR/EN/ES
- Post strategic comments with links to PlyChan videos
- Max 10 comments per run (up from 3)
- Track commented video IDs to avoid duplicates

### 2. Auto-Reply to Comments
- Automatically reply to ALL comments received on our videos
- 4 reply templates per language (fr/en/es)
- Avoids replying to our own comments
- Skips already-replied threads

### 3. Multi-Platform Publishing
- Facebook: 3 posts/day (FR/EN/ES) with blog links
- Medium: publish articles (requires MEDIUM_TOKEN)
- Reddit: search + post comments (requires REDDIT_CLIENT_ID)
- Twitter: search tweets (posting requires OAuth 1.0a)

### 4. Thumbnail Optimization
- Generate 3-4 word thumbnail text from video content
- Extract numbers and key terms
- Different from title (no duplication)

### 2. Facebook Posts
- Share blog articles with video links
- Post in relevant Facebook groups
- Use engagement hooks (questions, polls)

### 3. Twitter/X
- Search for economic tweets
- (Posting requires OAuth 1.0a User Context tokens)

### 4. Reddit
- Find relevant posts in r/economy, r/finance, r/investing
- (Posting requires Reddit API credentials)

## Tracking
All promotion activity is tracked in `output/promotion_tracker.json`:
- YouTube comments posted
- Facebook posts created
- Reddit posts found
- Twitter tweets found

## Best Practices
1. Post max 3-5 comments per day per platform
2. Vary comment text to avoid spam detection
3. Engage with replies to your comments
4. Track which platforms drive the most traffic
5. Focus on high-engagement content (videos with 1K-100K views)
6. Use long-tail keywords in comments
7. Always provide value, not just self-promotion

## Monetization Tips
- Enable YouTube monetization (1K subs + 4K watch hours)
- Use affiliate links in video descriptions
- Create sponsored content once you have 10K+ subs
- Diversify revenue: AdSense + sponsorships + affiliate + Patreon
- Focus on high-CPM niches: finance, investing, crypto, real estate
- Post consistently (3x/week minimum)
- Engage with community daily
- Collaborate with other creators in the niche
PYEOF
echo "Created SKILL.md"