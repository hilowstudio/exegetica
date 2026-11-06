# Investing data: live sources for the Economics investing unit

**Status:** research pass, 2026-10-19. Nothing built yet.
**Why this is separate:** the Social Sciences Mode is self-hosted (see `social-sciences-sources.md`). Current prices change every second, so the investing unit is the one deliberate exception: these tools call outside sources at question time. Each pick below was checked for a free tier and for terms that allow showing the data to students in a non-commercial school app.

## The short answer

Every investment type has a usable free source except one: **current U.S. stock quotes.** Every free stock-price tier we checked is either personal-use only or forbids display and redistribution. Two providers allow exceptions in writing (Finnhub, and Alpha Vantage, which advertises access for educational projects), so stock quotes wait on a permission email. Everything else is government data or a provider whose free tier allows display with attribution.

## Picks by investment type

| Investment type | Primary | Backup | Key? | Freshness | Must show |
|---|---|---|---|---|---|
| **Stocks and ETFs (prices)** | Finnhub, after written approval | Alpha Vantage (educational access), or Marketstack free (non-commercial, end of day, 100 calls/month) | Yes | Real-time (Finnhub) | Per approval terms |
| **Company fundamentals, dividends** | SEC EDGAR APIs (company facts, filings) | none needed | No (User-Agent with contact email) | Within about a minute of filing | Source line |
| **Currencies (forex)** | Frankfurter v2 with ECB rates (open source, can self-host) | ExchangeRate-API open endpoint | No | Daily | ExchangeRate-API needs an attribution link |
| **Precious metals** | metalpriceapi free (gold, silver, platinum, palladium; 100 calls/month) | metals.dev, or gold and silver ETFs once stock quotes are approved | Yes | Daily | "metalpriceapi.com" attribution |
| **Cryptocurrency** | CoinGecko Demo (100/min, 10,000/month) | CoinMarketCap Basic | Yes | About 1-5 minutes | "Powered by CoinGecko" |
| **Treasuries and interest rates** | Treasury daily yield-curve feed + Fiscal Data API (bills, average rates) | FRED (Treasury series only) | No | Daily | FRED notice if FRED is used |
| **Savings and CDs** | FRED national savings and CD rate series (public-domain series) | FDIC National Rates page (monthly) | FRED: yes | Monthly | FRED notice |
| **I-bonds and EE bonds** | TreasuryDirect rates page | none | No | Changes May 1 and Nov 1 | Source line |
| **Real estate (prices, rents)** | Zillow Research ZHVI and ZORI (CSV downloads) | FHFA House Price Index | No | Monthly | Zillow attribution required |
| **Mortgage rates** | Freddie Mac PMMS | FRED MORTGAGE30US (citation required) | No | Weekly (Thursday) | Freddie Mac attribution, no alteration |
| **REITs** | Treat as stocks | | | | |
| **Startups and seed capital** | SEC EDGAR Form D (private offerings: who's raising, how much) | SEC Regulation Crowdfunding (Form C) datasets | No | Within days of filing | Source line |
| **Mutual and index funds** | Alpha Vantage (fund and ETF profiles), with educational approval | SEC Mutual Fund Risk/Return datasets (expense ratios; quarterly) | Yes / No | Daily / quarterly | Per approval terms |
| **Energy commodities (oil, gas)** | EIA Open Data API | none needed | Yes (free) | Daily to weekly | "Source: U.S. Energy Information Administration" |
| **Agricultural commodities** | USDA AMS MyMarketNews (daily local cash prices, grain and livestock) | USDA NASS Quick Stats (monthly prices received) | Yes (free) | Daily / monthly | NASS "uses the NASS API but is not endorsed" notice |
| **Inflation** | BLS API v2 (CPI) | none needed | Yes (free) | Monthly | Source line |
| **Retirement accounts** | IRS limits, stored with a date (2026: 401(k) $24,500; IRA $7,500) | none | No | Yearly (2027 limits due late Oct-Nov) | Source and date |

## What doesn't exist for free

- **Current stock quotes licensed for a school to display**, without a written exception (see emails below).
- **Venture capital valuations and priced rounds.** Form D shows who is raising money and how much has been sold, never the valuation. Crunchbase no longer issues free keys, and its paid license forbids passing data on. PitchBook and CB Insights are paid.
- **Daily mutual fund prices (NAVs)** from an official, redistributable source.
- **Official gold and silver benchmark prices.** LBMA prices are licensed, and FRED dropped them in 2022.

## Excluded

| Source | Why |
|---|---|
| Alpha Vantage free tier (without approval) | "personal, non-commercial use"; use by an organization counts as commercial |
| Massive (formerly Polygon.io), Twelve Data, Tiingo | Free plans are individual-use or bar display |
| Yahoo Finance / yfinance | No official API; personal use only |
| IEX Cloud | Shut down August 2024 |
| Open Exchange Rates, exchangerate.host | Personal or non-commercial with tight limits; better options exist |
| Binance | Blocks U.S. and many cloud-server IP addresses |
| Crunchbase | No new free keys; license forbids passing data on |
| RentCast | Allows display, but 50 calls a month is too few for a class |

## Required notices

- FRED: "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis." Use only FRED series without a third-party copyright flag (the Treasury, savings, and CD series are fine; S&P and ICE BofA series are not). FRED's site-wide legal page restricts storing its content, so call FRED live and don't cache it in our databases.
- USDA NASS: "This product uses the NASS API but is not endorsed or certified by NASS."
- CoinGecko: "Powered by CoinGecko," shown prominently.
- metalpriceapi, Zillow, Freddie Mac, ExchangeRate-API: attribution.

## Permission requests

- **Finnhub** (support@finnhub.io): written approval for classroom display of free-tier quotes.
- **Alpha Vantage** (premium@alphavantage.co): its support page offers unlimited requests "for verified open-source or educational projects."

## Not verified

Finnhub's official rate-limit page; Financial Modeling Prep's terms (blocked); Marketstack's full terms and multi-symbol calls; GoldAPI.io's free plan; Coinbase's current market-data terms; Redfin's and AMS's terms; HUD's notice wording; whether SEC Mutual Fund datasets tag expense ratios cleanly.
