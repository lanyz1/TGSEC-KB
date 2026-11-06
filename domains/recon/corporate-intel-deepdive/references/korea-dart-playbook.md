# Korea DART Playbook — dart.fss.or.kr

DART is the Korean FSS electronic disclosure system: full-text securities filings of listed and major unlisted companies. The highest-value primary source for Korean entities — deal terms, counterparty financials, officers, schedules all live here.

## Full-text extraction recipe
1. Search page: `https://dart.fss.or.kr/dsab007/main.do`.
   - Company field `#headTextCrpNm` (회사명/종목코드), report name `#headReportName`, body text `#headContentWord`.
   - Submit by calling `headSearch()` (the 검색 button's onclick handler).
2. In result rows, the report link is an `<a>` with `href="/dsaf001/main.do?rcpNo=<14digits>"` or `onclick="openReportViewer('<14digits>','')"`.
   - Extract with regex `/rcpNo=(\d{14})/` or `/openReportViewer\('(\d{14})'/`.
   - **rcpNo is exactly 14 digits** (date + serial). NEVER derive it with `replace(/[^0-9]/g,'')` — path text like `dsaf001` prepends bogus digits, and a wrong ID renders a bare "거부" (refusal) page that looks like a block but is actually a malformed request. Re-read the raw href before concluding anything about rate limits or IP blocks.
3. Open `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=<rcpNo>`; wait ~5s. The document renders inside same-origin iframe `#ifrm`.
4. Extract text (verified working):
   ```js
   (() => { const f = document.querySelector('#ifrm');
     const d = f.contentDocument || f.contentWindow.document;
     return (d.body.innerText || '').slice(0, 4000); })()
   ```
   Batch several rcpNos in one browser loop (goto → sleep 5s → grab). If `#ifrm` is null, wait longer; if the page title reads "거부", re-read the raw href first — malformed IDs render a refusal page. If a verified 14-digit ID intermittently refuses or renders blank, lower concurrency and retry after a pause (transient throttle/late render); don't rewrite the ID, and don't conclude 'blocked'.
5. Once loaded, the iframe's `src` carries the underlying `/report/viewer.do?rcpNo=...&dcmNo=...` URL — fetchable directly for raw HTML if needed.
6. English mirror: `https://englishdart.fss.or.kr/dsbh001/main.do?rcpNo=<rcpNo>`.
7. Result lists show only the most recent ~15 filings. To reach older ones: open any recent related filing and follow the "※ 관련공시" (related disclosure) anchors inside the document body — they carry full rcpNo links. If using search date filters, verify the result set actually changed before trusting them.

## Filing type → intelligence table
| Korean report name | Meaning | Data to extract |
|---|---|---|
| 타법인주식및출자증권취득결정 | Acquiring shares in another company | Target profile (name/nationality/representative/capital/total shares), shares acquired, amount, stake %, method, purpose, closing date, board date, payment conditions |
| 주요사항보고서(전환사채권발행결정) | Convertible bond issuance | Amount, coupon/maturity rates (often 0%), maturity date, conversion price & window, dilution %, use-of-proceeds breakdown — usually reveals what the money buys |
| 주권관련사채권의취득결정 | Buying another company's equity-linked bonds | Issuer 3-year financial table, amount in original currency + disclosed FX rate, conversion terms, settlement date |
| 타인에대한채무보증결정 | Debt guarantee for a subsidiary | Debtor, creditor bank + branch, amounts, guarantee period, debtor financials, cumulative guarantees |
| 특수관계인에대한출자 | Capital injection to related party (Fair Trade Act §26) | Counterparty, share count, amount, schedule, purpose |
| 투자판단 관련 주요경영사항 | Material investment decision (frameworks/partnerships) | Agreement title and type (binding vs MoU), partner, structure, board date |
| 유상증자또는주식관련사채등의발행결정 / 발행결과 | Issuance decision / result | Planned vs final amounts, payment completion date |

## Extraction notes
- Harvest people: 대표이사/대표자 (legal representative), 작성책임자 (report author + department + phone) — real org-chart leads.
- Embedded financial tables (발행회사의 요약 재무상황 / 채무자의 요약 재무상황) give 3 years of counterparty/subsidiary numbers — often the only public financials for unlisted entities.
- Convert disclosed KRW figures back with the stated FX rate to recover original amounts (e.g. AUD deals).
- "※ 관련공시" lines cite prior filings — hop them to reconstruct the full history of a deal (framework agreement → detailed terms → execution).
- Companion systems: KIND (kind.krx.co.kr) for exchange notices; DART English pages to translate standard headings.

## Related sources
- Google Patents JSON XHR (for JS-rendered patent search): `https://patents.google.com/xhr/query?url=q%3D<urlencoded query>%26assignee%3D<urlencoded assignee>` returns JSON.
- Company IR sites and subsidiary-country websites — photos, addresses, officer names the filings lack.
