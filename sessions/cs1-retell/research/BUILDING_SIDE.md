# DIZA – Everyday customer research (buildings + hotels)

Researched 2026-10-17 for the USC InnovateLA "Resilience Comms" track (Retell AI). Produced by a separate Claude research agent from the prompt in this session; pasted in by the team.

**Tags:** [V] = primary/official source or peer-reviewed. [S] = secondary (news, vendor marketing, blog). [UNVERIFIED] = could not confirm.
**Calc** = our own arithmetic on a cited figure (shown so you can check it).
Where a number does not exist publicly, this report says so instead of estimating.

---

## 1. One-page summary

### The 3 strongest numbers

1. **Requests are frequent and slow.** Across 193,000+ US maintenance requests (2018–2026), renters filed **3.3 requests per unit per year** in 2024 (3.23 for multifamily), and the **median request took 13.1 days to close** (average ~50 days). [S] ([Hemlane, first-party data](https://hemlane.com/resources/rental-property-maintenance-data/))
   *Calc:* LA's 661,851 rent-stabilized units [V] ([LA City Controller](https://controller.lacity.gov/landings/rso/rso-analysis)) × 3.23 ≈ **2.1 million requests a year in RSO buildings alone.**
2. **The callers often don't speak English well.** In LA County, **2,187,790 people age 5+ (about 23.6%) speak English less than "very well"**; among Korean speakers it is ~60%, Vietnamese ~63%, Chinese ~57%, Spanish ~42%. [S, republishing Census ACS 2024 1-year] ([LA Almanac](https://www.laalmanac.com/population/po47.php)). **55.1%** of county residents speak a language other than English at home. [V] ([Census QuickFacts](https://www.census.gov/quickfacts/fact/csv/losangelescountycalifornia/POP815224))
3. **A slow leak response is expensive.** Water damage/freezing claims average **$15,400 per claim** (2019–2023) and were **22.6% of all homeowners losses** in 2023. [V] ([Triple-I, data from ISO/Verisk](https://www.iii.org/fact-statistic/facts-statistics-homeowners-and-renters-insurance)) *Caveat:* homeowners policies only; renters/condo policies are excluded from that table.

Supporting structural fact: California only requires an on-site resident manager when an absentee-owned apartment house has **16 or more units** (or a hotel has 12+ rooms); a 5–15 unit building just posts the owner's or agent's name and address. [V] ([25 CCR § 42](https://regulations.justia.com/states/california/title-25/division-1/chapter-1/subchapter-1/article-5/section-42/)) LA has **127,240 RSO units in 5–10 unit properties** and **97,641 in two-unit properties**. [V] ([LA City Controller](https://controller.lacity.gov/landings/rso/rso-analysis)) Those are the buildings where a phone call at 11 pm reaches nobody.

### Who pays and how much

- **Residential:** owner or property-management company. Comparable intake/answering layers cost **$1.00–$1.50 per unit per month**:
  - Buildium Maintenance Contact Center (human agents, 24/7): **$1.10/unit/month** for all maintenance calls, $140/month minimum. [S] ([Buildium](https://www.buildium.com/maintenance-contact-center/))
  - Property Meld MAX On-Call (AI intake): **$1.50/unit** add-on on a $2.00/unit Ops plan, $200/month minimum. [S] ([Property Meld pricing](https://propertymeld.com/pricing/))
  - For scale, whole PM suites: Yardi Breeze **$1/unit/month** ($100 min) [S] ([Yardi Breeze](https://www.yardibreeze.com/pricing/)); AppFolio **$1.49–$5.00/unit/month**, 50-unit minimum [S] ([AppFolio](https://www.appfolio.com/pricing)).
- **Hotels:** GM / ownership group. Canary AI Voice **from $300/month** [S] ([Hotel Tech Report](https://hoteltechreport.com/compare/canary-ai-voice-vs-heyhotelai-voice-text-agents)); Duve **$120–$200/month** minimums [S] ([Duve](https://duve.com/pricing/)); Akia **~$43/month** entry tier per property [S] ([roommaster, a competitor](https://www.roommaster.com/blog/akia-pricing)).
- **Realistic DIZA price point:** ~$1–1.50/unit/month or a flat ~$100–150/month small-building minimum, matching what Buildium and Property Meld already charge. (Our inference, not a sourced figure.)

### Our clearest differentiator (blunt)

**There is no single feature that nobody else has.** Multilingual AI voice for tenants exists (EliseAI: 33 languages [S]), and so does AI duplicate-ticket prevention (Entrata claims it [S]). Hotel AI voice is crowded (Canary, HiJiffy, HelloShift, PolyAI and others).

What is still open is a **segment + combination**:
1. **Small, independent LA buildings (under 16 units, often no on-site manager)** that are below the 50-unit minimums of AppFolio and outside enterprise tools like EliseAI/Entrata/RealPage.
2. **Phone-first, any language, no app or portal**, for the 23.6% of LA County residents with limited English.
3. **Visible cross-referencing** ("3rd leak report on floor 4 this week") on a ranked dashboard, plus a **dated ticket trail mapped to California repair deadlines** (Civil Code §1942's 30-day presumption, §1942.4's 35-day rule, LA anti-harassment penalties of $2,000–$10,000 per violation).
4. **The same engine runs crisis surges** – nobody in the PM or hotel market pitches that, and it's the story the Resilience track wants.

---

## 2. Findings A–D

### A. Residential buildings

#### A1. Volume
| Metric | Finding | Tag / source |
|---|---|---|
| Requests per unit per year | 3.3 overall in 2024 (2.93 in 2020); 3.23 multifamily, 3.40 single-family. Based on 193,000+ requests, all 50 states, Aug 2018–May 2026. | [S] [Hemlane](https://hemlane.com/resources/rental-property-maintenance-data/) |
| Data scale elsewhere | Property Meld benchmarks draw on 10M+ work orders but don't publish per-unit volume. | [S] [Property Meld 2025 annual report](https://propertymeld.com/wp-content/uploads/2026/03/PM25-Annual-Benchmarking-Report-2025.pdf) |
| Share urgent/emergency | **No independent figure found.** One AI-receptionist vendor claims 10–20% of maintenance calls are emergencies, sourced only to its own 2026 "benchmark." Treat as weak. | [S, weak] [My AI Front Desk](https://www.myaifrontdesk.com/property-management/facts/emergency-maintenance-call-share) |
| Share after-hours | No residential figure found. In hotels, one vendor's 15 months of AI-answered calls showed about 1 in 4 arrived outside 8am–6pm. | [S] [HelloShift](https://www.helloshift.com/news/hotel-ai-voice-adoption-2026-trends) |
| Share duplicates / same root cause | **No published figure exists** that we could find. This is the number DIZA should measure in its pilot. | [UNVERIFIED] |

#### A2. Staffing
- **Units per maintenance tech:** UpKeep recommends 2 technicians per 100 units and says some complexes run 1 per 500; it cites no source and its own meta description contradicts it (1 per 150–200). [S, uncited] ([UpKeep](https://upkeep.com/learning/technicians-per-apartment-unit/)) No NAA/NMHC primary ratio found. [UNVERIFIED]
- **Labor shortage:** about 24% of multifamily owners/managers were understaffed for maintenance; almost half found hiring difficult and 45% found retention difficult; over 30% said slow repairs hurt residents (Parks Associates + GE Appliances, 2023). [S] ([Bisnow](https://www.bisnow.com/news/national/property-management/maintenance-labor-shortage-pervasive-multifamily-industry-survey-118672))
- **No on-site manager in small buildings:** required only at 16+ units (absentee owner) or 12+ hotel rooms; 5–15 units only need a posted owner/agent notice. [V] ([25 CCR § 42](https://regulations.justia.com/states/california/title-25/division-1/chapter-1/subchapter-1/article-5/section-42/))
- **How many small buildings:** LA's RSO covers ~624,000 units in 118,000 properties [V] ([LAHD](https://housing.lacity.gov/residents/what-is-covered-under-the-rso)) — *Calc:* ~5.3 units per property on average. The Controller counts 661,851 RSO units (2024), with 97,641 in two-unit properties and 127,240 in 5–10 unit properties. [V] ([LA City Controller](https://controller.lacity.gov/landings/rso/rso-analysis))
- **After-hours coverage:** no survey of what share of buildings have it. The fact that Buildium, Yardi Breeze Premier and Rent Manager all sell a 24/7 call-center add-on suggests it's not built in. [S] ([Buildium](https://www.buildium.com/maintenance-contact-center/), [Yardi Breeze](https://www.yardibreeze.com/pricing/), [Rent Manager](https://www.rentmanager.com/pricing/))

#### A3. Response, lost requests, satisfaction, renewals
- **Resolution time:** median 13.1 days; fastest categories rekey/locks 7.9 days, HVAC 9.6, plumbing 9.9; roof 33.9. [S] ([Hemlane](https://hemlane.com/resources/rental-property-maintenance-data/))
- **Repair speed (Property Meld users):** 6.81 days in 2025 vs 6.32 in 2024 (labels partly unclear in the PDF). AI intake (MAX) calls average **132 seconds**, satisfaction 4.55/5. [S] ([Property Meld 2025](https://propertymeld.com/wp-content/uploads/2026/03/PM25-Annual-Benchmarking-Report-2025.pdf))
- **Lost/repeated requests:** **no published rate found.** [UNVERIFIED]
- **Maintenance in reviews:** share of apartment reviews complaining about maintenance fell from 22.1% (2003) to 7.8% (2022), but J Turner says maintenance complaints have risen since 2020 (1.4M reviews). [S] ([Multifamily Executive](https://www.multifamilyexecutive.com/property-management/j-turners-ai-model-analyzes-1-4-million-reviews_o))
- **Management drives renewal:** 83% of residents say management affects future lease decisions (NMHC/Grace Hill 2024, 172,700+ responses). [S, vendor infographic of the survey] ([Grace Hill](https://info.gracehill.com/hubfs/All%20GH%20Website%20File%20Downloads/Multifamily%20Infographics%20and%20Checklists/Renter%20Preferences%20Survey_Infographic.pdf))
- **Renewal link:** SatisFacts named prompt response to calls/emails and follow-up on completed service requests as the biggest driver of renewal likelihood; it estimated 60% of turnover is controllable. These are **2009** figures. [S] ([Multi-Housing News](https://www.multihousingnews.com/increase-resident-retention-2/)) Property Meld puts maintenance "among the top three" renewal factors but gives no numbers. [S] ([Property Meld](https://propertymeld.com/blog/the-maintenance-to-renewal-connection-what-the-data-actually-shows/))
- **Turnover cost:** $3,976 per move-out in 2022 (lost rent $1,598, concessions $1,240, unit repair $775, marketing $364), from Zego's report. [S] ([Multifamily Dive](https://www.multifamilydive.com/news/it-costs-nearly-4000-to-replace-a-resident-when-they-leave/627619/)) Average retention 60% (Zego 2024, 1,600+ respondents). [S] ([Zego](https://www.gozego.com/press-news/zego-releases-fourth-annual-resident-experience-management-report/))
- **J.D. Power apartments / Kingsley maintenance-specific figures:** not found. [UNVERIFIED]

#### A4. Channels
- **Renters prefer email for non-emergency maintenance** (NMHC/Grace Hill 2024; no percentage given). [S] ([Multifamily Dive](https://www.multifamilydive.com/news/nmhc-survey-reveals-renters-top-preferences/700666/)) ⚠️ This cuts against phone-first for routine requests.
- 81% want to renew their lease online. [S] ([Grace Hill](https://info.gracehill.com/hubfs/All%20GH%20Website%20File%20Downloads/Multifamily%20Infographics%20and%20Checklists/Renter%20Preferences%20Survey_Infographic.pdf))
- Channel split: one vendor claims 45% phone / 35% portal / 20% text+email, from its own unpublished 2026 survey. [S, weak] ([My AI Front Desk](https://www.myaifrontdesk.com/property-management/facts/maintenance-request-channels)) No independent figure found. [UNVERIFIED]
- **Limited English (LA County, ACS 2024):** 2,187,790 of 9,282,796 people 5+ speak English less than "very well" (~23.6%). Share less than "very well" by language: Spanish 42.4%, Chinese 57.3%, Korean 59.6%, Vietnamese 62.7%, Armenian 45.6%, Tagalog 29.7% (shares calculated from listed counts). [S, republishing ACS] ([LA Almanac](https://www.laalmanac.com/population/po47.php))
- 55.1% speak a language other than English at home; 17.1% of residents are 65+; **93.0% of households have broadband**. [V] ([Census QuickFacts](https://www.census.gov/quickfacts/fact/csv/losangelescountycalifornia/POP815224))
- *Note:* we did not find the Census "limited English speaking household" share for LA County (table S1602) in a fetchable form. [UNVERIFIED]

#### A5. Legal duty (California / LA)
- **Untenantable conditions (Civ. Code §1941.1):** substantial lack of weatherproofing, working plumbing/gas, hot and cold water, heating, electrical, clean pest-free premises, garbage receptacles, floors/stairs/railings in repair. **New for leases signed, amended or extended on/after Jan 1, 2026:** working stove and refrigerator; recalled units must be repaired/replaced within 30 days of recall notice. [V] ([Civ. Code §1941.1](https://california.public.law/codes/civil_code_section_1941.1)) Door locks are not in the general list.
- **Repair-and-deduct (§1942):** after oral or written notice, if the landlord doesn't repair in a "reasonable time," the tenant may repair (up to one month's rent, max twice in 12 months) or move out; waiting **30 days** after notice is presumed reasonable. [V] ([Civ. Code §1942](https://california.public.law/codes/civil_code_section_1942)) → *A timestamped ticket proves when notice was received.*
- **No rent if cited and unfixed (§1942.4):** if an inspector gives written notice and the problem stays unfixed **35 days** later, the landlord can't collect rent, raise rent, or serve a 3-day notice; damages $100–$5,000 plus fees. [V] ([Civ. Code §1942.4](https://california.public.law/codes/civil_code_section_1942.4))
- **LA Tenant Anti-Harassment Ordinance:** failing to perform necessary repairs/maintenance is prohibited conduct; civil penalties **$2,000–$10,000 per violation**, up to $5,000 more for tenants 65+ or disabled, plus treble damages (LAMC §§45.32–45.35); covers all rental units in the City. [S, law firm summary] ([Tobener Law](https://www.tobenerlaw.com/los-angeles-tenant-anti-harassment-ordinance/))
- **REAP:** if LAHD-cited violations aren't corrected in time, a property can be placed in the Rent Escrow Account Program and tenants get a **10–50% rent reduction**. [V] ([LAHD](https://housing.lacity.gov/residents/what-is-reap-renters))
- **Why the ticket trail matters:** each of these turns on *when* the landlord knew. A dated, per-unit log of every call (including duplicates from neighbors) is the evidence either side needs. (Our inference.)

#### A6. Costs
- **Answering service:** Buildium human contact center $1.10/unit/month (all calls) or $0.70/unit (missed calls only) + $300 setup, $140/month minimum. [S] ([Buildium](https://www.buildium.com/maintenance-contact-center/))
- **AI intake:** Property Meld MAX On-Call $1.50/unit. [S] ([Property Meld](https://propertymeld.com/pricing/))
- **Per-call answering-service prices:** only vendor blogs; no reliable figure found. [UNVERIFIED]
- **Average repair cost:** ~$200 per request, which Hemlane itself calls a rough industry estimate. [S] ([Hemlane](https://hemlane.com/resources/rental-property-maintenance-data/))
- **Water damage:** average claim $15,400 (2019–2023), 1.50 claims per 100 house-years. [V] ([Triple-I / ISO](https://www.iii.org/fact-statistic/facts-statistics-homeowners-and-renters-insurance)) **We found no study measuring how much faster response reduces the claim amount.** [UNVERIFIED]

### B. Hotels

#### B7. Request volume and staffing
- **Guest requests per occupied room night:** **no public figure found.** ALICE/Grupo Posadas discuss request types (towels, bedding, temperature) but publish no rates. [S] ([Hospitality Technology](https://hospitalitytech.com/grupo-posadas-predicts-guest-needs-improves-hotel-operations))
- **Phone vs app/text share:** not found. [UNVERIFIED] Guests with the brand's app installed score 68 points higher on satisfaction (699 vs 631 of 1,000). [V] ([J.D. Power 2025 NAGSI via BusinessWire](https://www.businesswire.com/news/home/20250715487795/en))
- **Staffing (AHLA, Dec 2024–Jan 2025, 282 hoteliers):** 65% report shortages (76% in May 2024); front desk is the most critical shortage for 26% (housekeeping 38%, maintenance 13%); 9% severely understaffed. [S] ([Hospitality Net](https://www.hospitalitynet.org/news/4125946.html))
- **Missed calls:** a vendor page repeats a claim that 40–60% of hotel calls go unanswered, attributed to another vendor (Upriser.ai). [S, weak] ([HelloShift](https://www.helloshift.com/news/hotel-ai-voice-adoption-2026-trends))

#### B8. Response time and revenue impact
- 12% of stays had a problem (odor, noise, housekeeping, check-in); satisfaction fell 217 points (677 → 460) when one occurred (39,219 guests). [V] ([J.D. Power via BusinessWire](https://www.businesswire.com/news/home/20250715487795/en))
- Faster responses to e-complaints raised complaint satisfaction and return intent (446 guests). [V, peer-reviewed] ([Mattila & Mount 2003, IJHM](https://pure.psu.edu/en/publications/the-impact-of-selected-customer-characteristics-and-response-time/))
- A 1-point rise on ReviewPro's 100-point review index was associated with up to +0.89% ADR, +0.54% occupancy, +1.42% RevPAR (Cornell, Chris Anderson, 2012). [V] ([Cornell eCommons](https://ecommons.cornell.edu/items/d64bbbba-651a-4e13-a058-af3e2e82f4cf); [press release](https://www.hospitalitynet.org/news/4058547.html))
- **Typical hotel request response times:** no public benchmark found. [UNVERIFIED]

#### B9. Multilingual guests (LA)
- 2025: 49.5M visitors to LA, **6.4M international** (*Calc:* ~13%). Top markets: Mexico, China, Canada, Japan, UK, Australia, South Korea. [V] ([Discover Los Angeles](https://www.discoverlosangeles.com/visitors-to-los-angeles-generated-426-billion-in-business-sales-and-supported-more-than-530000-jobs))
- Plus hotel *staff* and local guests from the 23.6% limited-English population above.
- **Cost of language barriers at the front desk:** no figure found. [UNVERIFIED]

### C. Competitors

#### C10–C11. Competitor table

| Product | Segment | Voice? | Languages | Triage / dedupe? | Price | Gap DIZA fills |
|---|---|---|---|---|---|---|
| **EliseAI** (Maintenance + VoiceAI) | Large multifamily | Yes, resident + maintenance calls 24/7 | 33 (VoiceAI); maintenance page says EN/ES | Triage + emergency routing; dedupe not mentioned | Not published | Enterprise sale; nothing for a 6-unit building. [S] ([maintenance](https://www.eliseai.com/maintenance), [VoiceAI](https://eliseai.com/voiceai)) |
| **AppFolio** Realm-X Maintenance Performer | PM companies, 50+ units | Talks to residents; channel not stated | "Multiple" | Urgency rules, emergency escalation, troubleshooting; dedupe not mentioned | Suite $1.49–5.00/unit/mo, 50-unit min | Below 50 units; no stated cross-unit pattern view. [S] ([Realm-X](https://www.appfolio.com/product-demos/realm-x-performers), [pricing](https://www.appfolio.com/pricing)) |
| **Buildium** Maintenance Contact Center | Small–mid PMs | Yes, **human** agents 24/7 | Not stated | Agents judge emergency | $1.10/unit/mo, $140 min | Humans, not multilingual-by-default, no clustering. [S] ([Buildium](https://www.buildium.com/maintenance-contact-center/)) |
| **Yardi** Breeze (Premier) | Small–mid | 24/7 call center add-on (Premier) | Not stated | Online requests; no AI triage stated | $1/unit/mo; Premier $400 min | Call center price unlisted; portal-first. [S] ([Yardi Breeze](https://www.yardibreeze.com/pricing/)) |
| **RealPage** AI Facilities Agent / Resident Agent | Large multifamily | Voice for *technicians*; residents via separate agent | Not stated | Prioritizes by urgency; trends/exceptions, no explicit dedupe | Not published | Enterprise only. [S] ([RealPage](https://www.realpage.com/property-management-software/ai-facilities-agent/)) |
| **Entrata** Maintenance AI | Large multifamily | Text intake ("no phone calls required"); voice not stated | Not stated | Triage + **claims to prevent duplicate tickets** | Not published | Text, not voice; enterprise. [S] ([Entrata](https://www.entrata.com/products/maintenance-ai)) |
| **Rent Manager** | Small–mid | Call Center add-on (Anequim, 24/7); AI call summaries | Not stated | Not stated | Quote only | Human call center bolt-on. [S] ([Rent Manager](https://www.rentmanager.com/pricing/)) |
| **Latchel** | Small–mid PMs | 24/7 maintenance support | Not stated | Emergency escalation settings | Plans not public; $500–1,000 setup | Price opaque; outsourced coordination. [S] ([Latchel](https://latchel.com/latchel-pricing)) |
| **Property Meld** MAX | Small–mid PMs | AI intake (avg call 132 s per benchmark) | Not stated | Triage, troubleshooting, 24/7; dedupe not mentioned | $2/unit Ops + $1.50 MAX, $200 min | Closest small-PM analog; no cross-unit clustering stated. [S] ([MAX](https://propertymeld.com/meet-max), [pricing](https://propertymeld.com/pricing/)) |
| **Zuma** (Kelsey) | Multifamily leasing | Yes, but **transfers** maintenance calls | Not stated | Routes by issue type | Not published | Leasing tool, not maintenance. [S] ([Zuma](https://www.getzuma.com/voice-ai)) |
| **Vendoroo** | Small–mid PMs | Channel not stated | Not stated | Not described; vendor selection | Not published | Vendor-side, not intake. [S] ([Vendoroo](https://vendoroo.ai)) |
| **Visitt** | Commercial buildings | Not stated | Not stated | **Similarity + duplicate detection** across work orders | Not checked | Commercial, not residential. [S] ([Visitt](https://visitt.io/blog/ai-property-management-software)) |
| **Canary** AI Voice / Messaging | Hotels (20,000+) | **Yes**, front desk calls | 100+ (messaging) | Q&A, bookings, concierge; tickets/routing not stated | From $300/mo | Revenue/FAQ focus, not ops ticketing. [S] ([Canary](https://eu.canarytechnologies.com/products/hospitality-ai), [HTR](https://hoteltechreport.com/compare/canary-ai-voice-vs-heyhotelai-voice-text-agents)) |
| **ALICE** (Actabl) | Hotels | Phone intake not mentioned | Not stated | Guest request + task tracking | Not published | Staff-entered; no AI voice front door. [S] ([Mews marketplace](https://www.mews.com/en/products/marketplace/alice-app)) |
| **Akia** | Hotels | Voice AI paid add-on | Not stated | Tickets not mentioned | ~$43/mo entry | Messaging-first. [S] ([roommaster](https://www.roommaster.com/blog/akia-pricing)) |
| **Duve** | Hotels | Not in pricing tiers | Not stated | Not stated | $120–200/mo min | Check-in/upsell focus. [S] ([Duve](https://duve.com/pricing/)) |
| **HiJiffy** | Hotels | **Yes**, voice assistant since 2022 | 130+ claimed | Maintenance requests, room service, bookings via integrations | Not published | Crowded overlap; no stated clustering. [S] ([Apaleo store](https://store.apaleo.com/apps/hijiffy)) |
| **Quore** | Hotels | No | — | Work orders + guest requests; texting via Akia/Kipsu | From $171/feature/mo | Back-office; no AI intake. [S] ([Capterra](https://capterra.com/p/169445/Quore/)) |
| Other hotel AI phone agents | Hotels | Yes | — | — | — | HelloShift, Heyhotel (from $200/mo), PolyAI, Visito, Riviera (YC) all exist. [S] ([HelloShift](https://www.helloshift.com/news/hotel-ai-voice-adoption-2026-trends), [HTR](https://hoteltechreport.com/compare/canary-ai-voice-vs-heyhotelai-voice-text-agents), [Visito](https://www.traveldailynews.com/technology/visito-unveils-ai-phone-call-agent-for-hotels/), [Riviera](https://www.ycombinator.com/companies/riviera)) |

#### C12. Where DIZA is different vs copying (blunt)

**Copying (already exists):**
- AI voice that takes maintenance calls 24/7 → EliseAI, Property Meld MAX, AppFolio Realm-X.
- Multiple languages → EliseAI (33), Canary (100+), HiJiffy (130+).
- Urgency triage + emergency routing → nearly everyone.
- Duplicate-ticket prevention → Entrata claims it; Visitt does similarity detection (commercial).
- Hotel AI phone agent → at least 6 products. **Hotels are the weaker half of this pitch.**

**Actually different (or at least unclaimed in public material):**
- **Root-cause clustering shown to the manager** ("3 leak reports, floor 4, likely same pipe") rather than just suppressing duplicates. Nobody we checked advertises cross-unit, same-week pattern explanation in residential.
- **Small independent buildings** without a PMS subscription: phone number + dashboard, no app, no 50-unit minimum.
- **Compliance-shaped ticket trail** for California/LA deadlines (§1942, §1942.4, anti-harassment, REAP).
- **One engine for ordinary days and disasters.** That's unique for the track, even if it isn't what a landlord buys.

**Honest risk:** each of these is a feature an incumbent could add. The defensible part is segment focus (small LA buildings, limited-English tenants), not technology.

### D. Business

#### D13. Willingness to pay / who signs
- Market price for an intake layer: **$1.00–1.50/unit/month** (Buildium human center $1.10; Property Meld MAX $1.50). [S] (sources above)
- *Calc:* a 12-unit building at $1.50 ≈ $18/month, which is below every vendor minimum we found ($140–$200). So small buildings need a **flat monthly price (~$100–150)** or must be sold through the PM company that manages many small buildings.
- Hotels: AI voice/messaging tools list **$43–$300+/month per property** (Akia, Duve, Heyhotel, Canary). [S]
- **Who signs:** residential — the owner of a self-managed building, or the PM company (which may pass the cost to owners); hotels — GM for an independent property, the management company or brand for chains. *We found no survey on this; it's standard industry structure.* [UNVERIFIED]

#### D14. A pilot a small LA building or hotel could start next week
1. **Building info:** unit list, floor/stack layout (for "same pipe" clustering), on-call phone number(s), preferred plumber/locksmith, what counts as an emergency.
2. **Phone setup:** give tenants the DIZA number on a flyer in their languages, or forward the existing line after hours (Canary's setup also relies on call forwarding [S] ([Canary](https://eu.canarytechnologies.com/products/hospitality-ai))). Our Retell number already answers in EN/ES with KO/ZH lines (see `../SESSION_CONTEXT.md`).
3. **Consent + recording notice:** our agent already plays a fixed California recording notice (see `../SESSION_CONTEXT.md`); confirm with counsel. [UNVERIFIED legal detail]
4. **Dashboard access** for the owner/manager and an SMS alert for P0 (water, gas, no heat, lockout).
5. **Success metrics for 30 days:** calls answered after hours, median time to first human action, duplicates merged, language mix, and how many tickets would have hit the §1942 30-day line.
6. **Fallback:** "press 0 for a person" to the on-call phone; 911 instruction for gas/fire.

---

## 3. Competitor table

See **C10–C11** above.

## 4. Three pitch-ready sentences ("ordinary Tuesday")

1. "The average rental unit files about three repair requests a year, and the median one takes 13 days to close — DIZA answers the first call in the tenant's own language and puts it on the manager's screen in seconds." ([Hemlane, 193,000+ requests](https://hemlane.com/resources/rental-property-maintenance-data/))
2. "In Los Angeles County, more than 2 million people speak English less than very well, so a portal in English isn't a front door for a big share of tenants." ([LA Almanac, ACS 2024](https://www.laalmanac.com/population/po47.php))
3. "A water-damage claim averages $15,400, and when three neighbors report the same drip, DIZA tells the manager it's probably one pipe before it becomes one ceiling." ([Triple-I / ISO](https://www.iii.org/fact-statistic/facts-statistics-homeowners-and-renters-insurance))

## 5. What would contradict our idea

- **Renters say they prefer email for non-emergency maintenance** (NMHC/Grace Hill 2024) and 81% want online renewals; LA County has 93% broadband. Phone-first may only matter for urgent, after-hours, older or limited-English callers. [S]/[V] ([Multifamily Dive](https://www.multifamilydive.com/news/nmhc-survey-reveals-renters-top-preferences/700666/), [Census](https://www.census.gov/quickfacts/fact/csv/losangelescountycalifornia/POP815224))
- **Incumbents bundle AI into the software owners already pay for** (AppFolio Realm-X is listed inside its plans; Property Meld MAX is $1.50 more). A standalone tool has to beat "free with my PMS." [S] ([AppFolio](https://www.appfolio.com/pricing))
- **Duplicate prevention is already claimed** by Entrata, so "dedupe" alone isn't a moat. [S] ([Entrata](https://www.entrata.com/products/maintenance-ai))
- **Small owners may not pay at all**: our $1.50/unit math gives ~$18/month for 12 units, under every vendor minimum.
- **Hotels are crowded** with AI phone agents (Canary at 20,000+ hotels claimed). [S] ([Canary](https://eu.canarytechnologies.com/products/hospitality-ai))
- **Managers may not want more calls:** if every "my sink drips" call pings them, it adds noise. The ranked dashboard has to *reduce* interruptions, or this fails.
- **AI intake works already:** Property Meld reports 4.55/5 satisfaction on AI intake calls — proof of demand, but also proof the slot is filled for PM companies that use it. [S] ([Property Meld](https://propertymeld.com/wp-content/uploads/2026/03/PM25-Annual-Benchmarking-Report-2025.pdf))

## 6. Open questions and unverified items

**No public figure found (measure these in the pilot):**
- Share of requests that are duplicates / same root cause.
- Share of residential requests that are emergencies, and share after hours (only a weak vendor claim of 10–20%).
- Rate at which requests get lost or must be repeated.
- Hotel guest requests per occupied room night; phone vs app share; typical hotel response times.
- Cost of language barriers at the front desk.
- Reduction in water-damage cost per hour of faster response.

**Not verified / weak:**
- Units per manager / tech (only uncited UpKeep advice).
- Channel split (45/35/20) — single vendor's unpublished survey.
- Census "limited English speaking households" share for LA County (S1602) — not fetched.
- Canary, ALICE, HiJiffy, EliseAI, Entrata, RealPage, Latchel, Vendoroo, Zuma pricing — not published.
- Whether EliseAI or AppFolio do cross-unit clustering in practice (marketing pages don't say; a demo would).
- Who signs (owner vs PM vs GM) — industry norm, no survey.
- Renewal data linking maintenance speed to renewals is old (2009 SatisFacts) or qualitative.
- California call-recording consent details for the pilot — confirm with counsel.

**Next steps that would strengthen the pitch:** call 3–5 small LA landlords/PMs and ask how many after-hours calls they get a month and how often neighbors report the same problem; request an EliseAI/AppFolio demo to confirm whether they cluster related tickets.
