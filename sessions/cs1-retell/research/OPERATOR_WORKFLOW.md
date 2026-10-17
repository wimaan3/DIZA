# What 911 call-takers do, and where the time goes

- **Session:** cs1-retell (research subagent), 2026-10-17
- **Purpose:** DIZA is refocusing on **supporting** 911 call-takers and dispatchers, not replacing or filtering them. This file records the real bottlenecks, with numbers, so the tool targets one of them.
- **Builds on:** `EXISTING_INFRASTRUCTURE.md` in this folder. That file already covers NENA §4.1 answer times, §4.1.2 location first, §5.4 callbacks, §5.5.5–5.5.6, §5.6.2 AI for non-emergency, ANI/ALI and Phase II, RapidSOS/Carbyne/Prepared basics, HIE and contingency routing, and 211 LA. None of that is repeated here except as a one-line pointer.
- **Verification key (same as before):** **[V]** = read in an official or primary source (agency report, standard, peer-reviewed abstract). **[S]** = secondary source only (news, vendor, trade press). **[UNVERIFIED]** = could not confirm. **[EST]** = our own estimate, with no source. Never put [EST] on a slide as fact.
- **Main primary documents read in full text for this file:**
  - LAPD Communications Division, *Improving 9-1-1 Call Response Times*, fact sheet dated 30 Oct 2025, transmitted to City Council 3 Feb 2026 (CF 23-0255-S1). [PDF](https://cityclerk.lacity.org/onlinedocs/2023/23-0255-S1_misc_02-03-26.pdf)
  - LA City Council motion (Raman), 22 Apr 2025, CF 23-0255-S1. [PDF](https://cityclerk.lacity.org/onlinedocs/2023/23-0255-S1_misc_04-22-25.pdf)
  - LAPD, *2025 Palisades Fire After-Action Report*, 21 Oct 2025. [PDF](https://www.lapdpolicecom.lacity.org/110425/BPC_25-305x.pdf)
  - LAFD, *Palisades Fire After Action Review Report*, 8 Oct 2025. [PDF](https://lafd.org/sites/default/files/pdf_files/Palisades_AARR_10_08_2025_final.pdf)
  - NENA-STA-020.2-2026, *9-1-1 Call Processing*, §§3–5. [PDF](https://cdn.ymaws.com/www.nena.org/resource/resmgr/standards/standards1/NENA-STA-020.2-2026_911CallP.pdf)
  - Meischke et al., "The effect of language barriers on dispatching EMS response", *Prehospital Emergency Care* 2013 (abstract). [PubMed 23952940](https://pubmed.ncbi.nlm.nih.gov/23952940/)

---

## (a) One-page summary: the three biggest operator bottlenecks

### Bottleneck 1. Not enough call-takers, so callers wait in a queue with nothing captured

- **LAPD answered only 57.43% of 911 calls within 15 s in 2024.** The state/NENA target is 90%. In 2023 the figure was 54.8%. **[V]** ([Council motion, Apr 2025](https://cityclerk.lacity.org/onlinedocs/2023/23-0255-S1_misc_04-22-25.pdf); [NBC LA, Feb 2024](https://www.nbclosangeles.com/investigations/shortage-of-9-1-1-operators-in-la-is-straining-emergency-response-system/3352100/))
- **LAPD received 2,948,076 911 calls in 2024 and answered 2,400,789.** **[V]** ([LAPD fact sheet](https://cityclerk.lacity.org/onlinedocs/2023/23-0255-S1_misc_02-03-26.pdf)) The gap is about 547,000 calls (18.6%). The report doesn't break the gap down. It probably consists mostly of callers who hung up before answer, plus repeat dials. That breakdown is **[UNVERIFIED]**.
- **Staffing:**
  - LAPD needs **100 emergency board operators per 24 h** to meet 90%/15 s at an average of **332 emergency calls an hour**.
  - It had **92 PSR vacancies** on 29 Oct 2025.
  - Training takes **about one year**.
  - Hiring fell from 144 trainees (2024) to 56 (2025).
  - Attrition was **11.9%** in January–August 2025.
  
  All **[V]** (LAPD fact sheet).
- **Non-emergency calls that come in on 911 wait an average of 3 min 40 s.** One burglary caller waited an hour. **[V]** (Council motion)
- **Nationally:** 74% of centers had open positions in 2025 (82% in 2024), 22% of trainees fail, and 79% of centers use the same staff for emergency and non-emergency calls. **[S]** ([EMS1 on NENA/Carbyne Pulse of 9-1-1 2025](https://www.ems1.com/research/ai-seen-as-lifeline-as-911-centers-report-rising-burnout-and-record-outages-survey-shows))

### Bottleneck 2. In a disaster, duplicate and third-party calls flood the queue and send units to the wrong places

- **Palisades fire, LAPD:**
  - LAPD logged **160+ evacuation-assistance calls**. Many were made by friends and family who could not reach loved ones.
  - Officers found that *"many of the calls were generated for individuals who had been successfully evacuated."* Cell networks were down or overloaded, *"and people were calling 911 when they could not verify that their loved ones had made it to safety."*
  - Communications Division had to create a manual **"master incident"** to group these calls.
  
  **[V]** ([LAPD Palisades AAR, p.15 and timeline 14:25](https://www.lapdpolicecom.lacity.org/110425/BPC_25-305x.pdf))
- **Palisades fire, LAFD:** at 19:05, Metro Fire Communications dispatched units to an elevator rescue at 15515 W Sunset *"without realizing that this address was also encompassed within the fire's affected area."* **[V]** ([LAFD AAR, p.35](https://lafd.org/sites/default/files/pdf_files/Palisades_AARR_10_08_2025_final.pdf))
- **UL Research Institutes (report for Gov. Newsom, Oct 2026):** *"the speed and scale of the event overwhelmed the 911 system … Calls came in faster than dispatch could manage or assign them."* For the Eaton fire, the report says that if 911 calls had been routed through the operations section chief, information on the fire west of Lake Ave *"could have been known and acted upon earlier."* **[S]** ([NBC News](https://www.nbcnews.com/news/us-news/los-angeles-fires-report-communication-failures-emergency-response-rcna601022), [Firehouse/LA Times](https://www.firehouse.com/operations-training/wildland/news/55409515/chaos-missteps-at-palisades-eaton-fires-found-during-ul-fsri-probe))
- **Superstorm Sandy:** FDNY received 7,377 calls on 29 Oct 2012, and only 1,945 were legitimate. Most of the rest were duplicates. **[S]** ([APCO PSC summary of NY Post](https://psc-legacy.apcointl.org/?p=16350))

### Bottleneck 3. Language and location verification are slow even when a human answers

- **Language:**
  - In Washington State 911 recordings, connecting to an interpreter took **49 s on average** from reaching the service operator.
  - With a language barrier, time to a BLS assignment was **33% longer** and time to an ALS assignment **43% longer**. When an interpreter was actually used, BLS time rose **82%**.
  
  **[V]** ([Meischke 2013](https://pubmed.ncbi.nlm.nih.gov/23952940/))
  - LAPD says getting an interpreter on the line can take **up to 45 s**. **[S]** ([LA Times via AOL](https://www.aol.com/news/city-officials-call-lapd-hire-110036429.html))
- **Location:**
  - In a survey of 1,014 PSAP staff, 48% said they only sometimes, rarely or never get accurate Phase II location. 82% had little confidence in displayed wireless location, and **79% said they need location within 15 s**. **[S]** (2014 Find Me 911 survey, [Fire Engineering](https://www.fireengineering.com/fire-safety/survey-of-911-dispatchers-finds-many-indoor-callers-cannot-be-located/)) The survey is old and comes from an advocacy group.
  - NENA requires the location to be **verified by read-back** and the callback number to be checked against the call-handling display. **[V]** (NENA §5.2.1)

**What this means for DIZA:** the best opening is the **time a 911 caller spends in the queue** before a human answers, plus **the first 30–60 seconds after answer**. The agent would gather and verify location, callback number, language and the caller's relationship to the incident, and it would flag a possible match to an existing incident. It would then hand the call-taker a pre-filled card, without ever setting priority, dispatching or dropping a call. LAPD's own plan matches this. It says AI *"will be a tool for PSRs … not an automated call-taking service"* and asks for *"who/what/where"* summaries and two-way translation. **[V]** (LAPD fact sheet, item 3)

---

## (b) Call-taker workflow, time per step, and what an intake agent may do before pickup

**Rules for the agent column.** "Before pickup" means while the caller would otherwise be waiting in the 911 queue, or on a non-emergency or overflow line. The agent may **gather and verify** information. It may **not decide** anything:
- no priority or determinant code
- no "not an emergency" disposition
- no dispatch
- no pre-arrival medical instructions beyond "stay on the line"
- no dropping or deflecting a 911 call

| # | Step (NENA / typical practice) | What the call-taker does | Typical time / standard | Intake agent before pickup? |
|---|---|---|---|---|
| 0 | Call arrival → answer | ACD queues the call. Order: 911 lines, then non-emergency, then admin (NENA §4.1.1) | **Standard:** 90% ≤15 s, 95% ≤20 s **[V]** NENA §4.1. NFPA 1225 (2022) uses 90% ≤10 s **[S]** ([USFA EFO paper](https://apps.usfa.fema.gov/pdf/efop/efo241929.pdf)). **LAPD actual:** 57.43% ≤15 s (2024) **[V]**. On a bad day, 45.30% (4 Aug 2024: 24 PSRs, 8,316 calls) **[V]**. Non-emergency calls on 911 averaged 3 min 40 s **[V]** | **Yes, this is the target window.** Greet in the caller's language and say a human is coming. Do **not** replace the human answer |
| 1 | Greeting and "Where is your emergency?" | Answer with "9-1-1". **Ask for and verify location first** (NENA §4.1.2 SHALL) | No national median found **[UNVERIFIED]**. AHA starts its T-CPR clock at **"address acquisition"**, which shows it's a distinct, measurable step **[S]** ([AHA](https://cpr.heart.org/en/resuscitation-science/telecommunicator-cpr/public-safety-answering-point-recommendations)). Dispatchers want it **≤15 s** **[S]**. **[EST] 15–60 s**, longer for wireless calls, callers who don't know where they are, and third-party callers | **Yes.** Capture the spoken address, read it back, geocode it, compare it with the device location if we have any, and offer an SMS GPS link. Mark "caller-confirmed" vs "unverified". The human still re-confirms it |
| 2 | Callback number | Ask for the number and compare it with ANI. If it differs, ask again. Document it (NENA §5.2.1) | **[EST] 5–10 s** | **Yes.** Read back ANI ("Is this the best number?") and capture an alternate number |
| 3 | Nature / chief complaint | "Tell me exactly what happened." Pick the protocol card or incident type | Part of processing: life-threat calls should be **dispatchable ≤60 s**, all other emergencies ≤90 s, measured from answer (NENA §5.1, SHOULD) **[V]**. NFPA 1710: ≤64 s, or ≤90 s with EMD **[S]** | **Gather only.** Record the caller's own words verbatim. Do **not** choose a card or code |
| 4 | Caller identity and relationship | Name. First-party, second-party or third-party? On scene or remote? | **[EST] 5–15 s**. This is critical in disasters, where many callers were relatives (LAPD AAR) **[V]** | **Yes.** Ask "Are you there now, or calling about someone else?" and "Who are they, and when did you last hear from them?" |
| 5 | Protocol interrogation (EMD/EFD/EPD key questions) | Scripted questions (conscious? breathing? weapons? people trapped?) leading to a determinant | Average EMD call processing was 93 s at one center (21% compliance) **[S]** (USFA EFO). In the FPRF/PCG national study, centers following NFPA 1225 averaged **1 min 18 s**, and centers following no standard averaged about **7 min** **[S]** ([NFPA Journal, Fall 2023](https://nxtbook.com/nxtbooks/nfpa/journal_2023fall/index.php?startid=33)) | **Partly.** Ask only universal safety facts (number of people, hazards such as fire/smoke/weapons/water, mobility or medical needs, someone trapped?). **Never** run licensed EMD logic or assign determinants |
| 6 | Language barrier handling | Conference in an interpreter (e.g., LanguageLine): dial, sometimes enter an account code, pick the language, wait | Average **49 s** to reach the interpreter after reaching the service **[V]** (Meischke). LAPD: **up to 45 s** **[S]**. Minnesota program average **<11 s** **[V state page]** ([MN DPS](https://dps.mn.gov/divisions/ecn/programs/911/Pages/language-integretation.aspx)) | **Yes.** Detect the language in the first sentence, run the whole intake in that language, and tell the call-taker "Korean speaker" before pickup so the interpreter can be pre-dialed |
| 7 | CAD entry | Type location, incident type, narrative and caller information into CAD (often while talking) | Concurrent with steps 1–5. Calls last **90 s to 4 min** on average **[S vendor]** ([Prepared/Axon](https://prepared911.com/blog/axon-911-intelligence-that-starts-the-moment-a-call-is-answered)) | **Yes, as a draft.** Pre-fill a card in EIDO-style fields (§8). The human accepts or edits it. Nothing is written to CAD without a human |
| 8 | Duplicate / existing-incident check | Does this match an open incident? (manually in CAD or on the map) | No measurement found **[UNVERIFIED]**. LAFD dispatched into the fire area unaware (LAFD AAR) **[V]**. Sandy: about 74% of calls weren't legitimate, mostly duplicates **[S]** | **Flag only.** Show "possible match: incident #123, 300 m away, 4 similar calls". Never merge or drop on its own (NENA §5.5.6 says each call is evaluated) |
| 9 | Transfer, if wrong PSAP/agency | Warm transfer. Relay location, callback number, nature and safety information (NENA §5.3) | Snohomish Co. average **21 s** per transfer (51 s before 2015) **[S]** ([HeraldNet](https://www.heraldnet.com/?p=344864)). LAPD: spill-over to secondary queues adds **10–30 s per incident** **[V]** | **Suggest only.** "Incident location is in Pasadena, so suggest the Pasadena PSAP" plus the card, ready to send with the warm transfer |
| 10 | Dispatch handoff | Call-taker to radio dispatcher (in CAD). Pre-alert allowed (NENA §5.1) | Inside the 60/90 s target | **No.** Human only |
| 11 | Pre-arrival instructions (PAIs) | Protocol instructions (CPR, bleeding, evacuation) until units arrive | AHA T-CPR benchmarks are measured **from address acquisition** to recognition and first compression. Public versions conflict (<60/<90 s vs <90/<120 s) **[S]** ([AHA](https://cpr.heart.org/en/resuscitation-science/telecommunicator-cpr/public-safety-answering-point-recommendations)) | **No.** Only generic safety lines ("stay on the line, a call-taker is coming; if you are in danger, move to safety") |
| 12 | Abandoned / dropped call | Call back at least once, same modality (NENA §5.4; see existing report) | Columbia-Richland SC: **23%** of 911 calls disconnected before answer in 2025 **[S]** ([JEMS](https://www.jems.com/ems-operations/just-no-one-picked-up-23-of-columbia-richland-sc-911-calls-disconnected-before-answer-in-2025/)) | **Yes, partly.** If the caller hangs up during intake, the partial card stays on the callback list for a human. Agent callbacks are local policy only |

**Summary of the table:** steps 1, 2, 4, 6 and part of 5 and 7 are **gather + verify**, so an agent can start them during queue time. Steps 3, 8 and 9 are **gather + suggest**. Steps 10–11 are human only.

---

## (c) Findings by question

### 1. The call-taker workflow and its timing

**What NENA 2026 now says** (new compared with the existing report, which only covered §4.1 and §4.1.2):
- **§5.1, processing:** calls with an imminent threat to life *"SHOULD be processed and dispatchable within 60 seconds. All other emergency calls … within 90 seconds."* The clock starts when two-way communication begins. A call is "dispatchable" when the essential information (location, incident type, urgency, caller information) has been **verified**. Pre-alerts are allowed. **[V]**
- **§5.2, minimum information:** the location SHALL be obtained. Callback number, nature of the emergency and caller identity SHOULD be obtained. **[V]**
- **§5.2.1, verification:**
  - A location counts as verified only when the telecommunicator *"has actively confirmed the accuracy … by prompting the caller to repeat or confirm the information back."*
  - The callback number is verified against the call-handling equipment. If it differs, the caller SHALL repeat it.
  
  **[V]**
- **§4.1.3, text calls:** the minimum fields are the address/location, caller name and callback number, type of emergency, **time of occurrence, hazards**, and **identity of those involved and their location**. **[V]**
- **§3.2:** NENA recommends using standard event codes from **APCO 2.103** (Common Incident Types). **[V]**

**Measured times:**
- The FPRF/PCG national study (published 2023) found centers following NFPA 1225 averaged 1 min 18 s from answer to dispatch, against about 7 min at centers following no standard. 65% vs 27% of calls were processed in under 60 s. These are averages, not medians, and law-enforcement calls were excluded. **[S]** ([NFPA Journal](https://nxtbook.com/nxtbooks/nfpa/journal_2023fall/index.php?startid=33)) **No national median call processing time was found. [UNVERIFIED]**
- Local examples: Greene Co./Bellbrook OH averaged 93 s for EMD (USFA EFO). Washington Co. TX averaged 25–47 s. **[S]**
- **Time to verify location:** no study measuring it was found. **[UNVERIFIED]**
- **Share of calls with inaccurate or missing location:**
  - In the 2014 survey, 48% of staff said Phase II location was accurate only sometimes, rarely or never. 97% of centers had received a call from someone who couldn't say where they were, and 40% get such calls regularly. **[S]** ([Fire Engineering](https://www.fireengineering.com/fire-safety/survey-of-911-dispatchers-finds-many-indoor-callers-cannot-be-located/), [RCR Wireless](https://rcrwireless.com/20140425/wireless/wireless-callers-hard-locate-911-dispatcher-survey-finds))
  - FCC data for Washington DC (Dec 2012–Jul 2013): only 10.3% of wireless calls carried lat/long. **[S]** ([Fierce](https://www.fierce-network.com/wireless/fcc-data-shows-9-out-10-911-calls-from-cell-phones-d-c-did-not-have-accurate-location-info))
  - Both figures predate device-based hybrid location (2018+), so current rates are **[UNVERIFIED]**. Most calls are wireless (NC 87.6%, CT 76.7% in 2023). **[V state data]** ([NC 911 Board](https://it.nc.gov/nc-911-call-statistics), [CT DESPP PDF](https://portal.ct.gov/-/media/despp/dset/911_statistical_reports/psaps_call_volume_2023_text.pdf))
- **Misroutes:** in the DC region about 100,000 calls a year need a transfer, and DC estimates about 5% of its 911 calls do. **[S]** ([NBC4 Washington, 2021](https://www.nbcwashington.com/investigations/nearly-100000-local-911-calls-each-year-sent-to-wrong-911-center-require-transfer/2646442/))

### 2. Surge behavior: what happens when every call-taker is busy

**Mechanics:**
- **Queues:**
  - 911 calls wait in an ACD queue. Non-emergency lines are answered only after 911 lines (NENA §4.1.1).
  - At LAPD, "Secondary" (non-emergency) PSRs **answer the 911 holding queue first**. Calls on 911 that turn out to be non-emergency are transferred to the Secondary queue.
  - LAPD rejected dedicated non-emergency operators because doing so would slow 911.
  - Spill-over between queues adds 10–30 s per incident.
  
  **[V]** (LAPD fact sheet, items 2 and 4)
- **Overflow and alternate routing:** when the primary PSAP can't take calls, they go to an alternate PSAP (NENA §5.5.4), which should transfer them back or process them and relay. Busy signals happen once trunks are exhausted. See the existing report. **[V]**
- **Abandonment:** callers hang up, and NENA §5.4 requires callback attempts (existing report). LAPD's gap between calls received and answered was about 18.6% in 2024. The cause breakdown is **[UNVERIFIED]**. Columbia-Richland SC had 23% disconnected before answer (2025). **[S]**
- **Callback lists:** NENA leaves the details to local policy. No LA-specific callback-list data was found. **[UNVERIFIED]**

**Documented cases:**

| Event | What happened at 911 | Source |
|---|---|---|
| **LA wildfires, Jan 2025 (LAPD)** | 160+ evacuation-assistance calls, many from relatives about people already evacuated. Cell networks were down or overloaded. A manual "master incident" was created at about 13:15. The Green Mountain repeater was shut down at 16:20 and units became hard to reach. A tactical alert came 45 min after the first calls. **No total call counts or wait times are published in the AAR** | **[V]** [LAPD AAR](https://www.lapdpolicecom.lacity.org/110425/BPC_25-305x.pdf) |
| **LA wildfires (LAFD)** | Units were dispatched into the fire area unaware of it. The DOC phone line was flooded by a media broadcast, with "up to 100 calls in the queue" and about one call every 30–60 s overnight (internal line, not 911) | **[V]** [LAFD AAR](https://lafd.org/sites/default/files/pdf_files/Palisades_AARR_10_08_2025_final.pdf) pp.35, 46–47 |
| **LA wildfires (ULRI)** | "Calls came in faster than dispatch could manage or assign them". Police dispatchers temporarily routed 911 calls through a captain's personal cellphone. LASD is replacing a 38-year-old dispatch system and hiring 80 dispatchers | **[S]** [NBC News, Oct 2026](https://www.nbcnews.com/news/us-news/los-angeles-fires-report-communication-failures-emergency-response-rcna601022) |
| **Eaton fire (Altadena)** | The first 911 calls from west of Lake Ave came at about 22:50–01:00. The evacuation alert went out at 03:25. 18 of 19 deaths were west of Lake. Two homebound disabled men died after three 911 calls. **No published wait or abandonment data for Pasadena or LASD** **[UNVERIFIED]** | **[S]** [Fire Engineering](https://www.fireengineering.com/firefighting/wildland-firefighting/eaton-fire-no-misconduct-delay-in-evacuation-notices-to-west-altadena-ca-report-says/), [LAist](https://laist.com/brief/news/climate-environment/despite-three-911-calls-two-homebound-disabled-men-died-in-the-eaton-fire-waiting-for-rescue), [Rep. Chu letter](https://chu.house.gov/sites/evo-subsites/chu.house.gov/files/evo-media-document/letter-to-board-of-supervisors-re-l.a-county-wildfires-independent-after-action-report-final-71.pdf) |
| **LA routine "surge"** | 4 Aug 2024: 24 PSRs, 8,316 calls, 45.30% answered ≤15 s. 4 Aug 2025: 34 PSRs, 8,152 calls, 64.52% | **[V]** LAPD fact sheet |
| **Maui, 8 Aug 2023** | 4,529 dispatch contacts against an average of about 1,600 a day. **12 dispatchers on staff out of 39 positions**. MPD: "three days' worth of calls within a single day". Callers who couldn't reach the non-emergency missing-person line called 911 | **[S]** (summaries of the [Maui County AAR](https://www.mauicounty.gov/DocumentCenter/View/146279/2023-Wildfire-After-Action-Report), which returned 403 to us; [Maui News](https://www.mauinews.com/news/local-news/2025/08/maui-police-release-final-report-on-2023-wildfire-with-recommendations/); [AP via NBC](https://www.nbcbayarea.com/news/national-international/911-calls-from-maui-capture-pleas-for-the-stranded-the-missing-and-those-caught-in-the-fires-chaos/3428627/)) |
| **Hurricane Harvey, 2017** | Houston received about 75,000 calls in roughly 24 h against a normal 8,000–9,000 a day. Harris County hold times averaged more than 2 min for 11 days, with one day averaging **22 min**. CAD outages forced handwritten slips. Officials cited more non-emergency calls | **[S]** [EMS1/AP](https://www.ems1.com/911/articles/houstons-911-lines-swamped-with-calls-amid-widespread-flooding-28JKVWOGhVNaVW9j), [KHOU](https://www.khou.com/article/news/investigations/could-problems-calling-911-during-harvey-happen-again-today/285-589328501), [Click2Houston](https://www.click2houston.com/news/2017/09/20/why-911-calls-in-harris-county-might-be-delayed/) |
| **Superstorm Sandy, 2012** | FDNY: 7,377 calls, 1,945 legitimate | **[S]** [APCO PSC](https://psc-legacy.apcointl.org/?p=16350) |

### 3. Staffing

- **IAED/NASNA survey (2022 data, 774 centers):**
  - 13 centers had 70%+ of positions vacant, 92 had 50–69%, and 166 had 30–49%.
  - 3,952 staff departed in 2022.
  - More than a third of centers had fewer positions filled than in 2019.
  
  **[S]** ([911.gov newsletter](https://www.911.gov/newsletters/issue-14/survey-more-than-half-of-911-centers-face-staffing-crisis), [Urgent Comms](https://urgentcomm.com/dispatch-call-taking/emergency-dispatch-centers-are-facing-a-staffing-crisis-report-says))
  - Motorola cites the same survey for "many PSAPs at 75% staffing". **[S]**
- **NENA:** an average shortage of about 30%, and 3–18 months of on-the-job training. **[S]** (Axios / KSHB quoting April Heinze)
- **Pulse of 9-1-1 2025 (NENA + Carbyne, 1,379 respondents):**
  - 74% of centers had open positions, down from 82%.
  - 22% of trainees fail.
  - Nearly 70% of staff feel stress before every shift.
  - 88% had an outage in the past year.
  - **86% are at least somewhat comfortable with AI assisting call-taking**, but only **4% use automated call screening**.
  - Translation and automated triage are the top AI priorities.
  
  **[S]** ([EMS1](https://www.ems1.com/research/ai-seen-as-lifeline-as-911-centers-report-rising-burnout-and-record-outages-survey-shows), [Carbyne PR](https://carbyne.com/resources/press/third-annual-pulse-of-9-1-1-report-finds-burnout-cyber-vulnerabilities-and-outdated-technology-threaten-emergency-service-readiness/))
- **LAPD:**
  - PSR II/III vacancies fell from 162 (Aug 2024) to 70 (Aug 2025).
  - There were 92 PSR vacancies on 29 Oct 2025, with 73 trainees in the pipeline and 11.9% attrition.
  
  **[V]**
  - Operators worked mandatory overtime. The hours aren't published. **[S]** (NBC LA 2024)
- **Overtime and hours elsewhere:** some counties report 12–16-hour days. **[S]** ([TechCrunch, Aug 2025](https://techcrunch.com/2025/08/27/911-centers-are-so-understaffed-theyre-turning-to-ai-to-answer-calls)) National overtime figures were **not found. [UNVERIFIED]**

### 4. Non-emergency load, diversion, and AI already deployed

**Share of calls that are non-emergency.** There's no single national figure, and the definitions differ:
- Vera Institute, 9 cities, 15.6M police calls for service: an average of **62.6% "noncriminal"** and ≤7% violent crime. **[S]** ([Vera](https://vera.org/publications/911-analysis))
- Motorola says non-emergency calls "can represent more than two-thirds" of PSAP volume. **[S vendor]** Aurelian's CEO estimates about 70%. **[S]**
- LAPD defines Priority III as routine calls (loud radio, trespass, car alarm, and so on). LAPD did not publish its own share. **[V definition]**

**Diversion that exists today:**
- **LA (LAPD fact sheet) [V]:**
  - The UMCR unarmed crisis teams took 4,599 diverted calls in 2024 and 10,740 from 1 January to 25 October 2025. They cover only 6 divisions, and a qualified PSR still has to interview the caller.
  - The CORS online reporting system took 72,447 reports in 2025.
  - 877-ASK-LAPD goes straight to the Secondary queue.
  - The 311 call center is open only 7am–7pm on weekdays.
- **988:** the Washington State pilot diverted nearly 2,000 911 calls to 988 in 4 months at 3 of 65 PSAPs. **[V state]** ([WA HCA PDF](https://hca.wa.gov/assets/program/cris-doh-mhccdi-midpoint-data-20240709.pdf)) No national 911-to-988 transfer rate was found. **[UNVERIFIED]**
- **Nurse navigation:** DC's Right Care Right Now triaged 62,000 low-acuity calls and diverted 40% (43% in 2022). **[S vendor GMR]** ([GMR](https://www.globalmedicalresponse.com/news/the-largest-nurse-navigation-system-in-the-country-celebrates-five-years-in-washington,-d-c)) There are no RCTs. **[S]** ([ACEP Now](https://acepnow.com/article/can-911-triage-nurses-improve-care-and-save-money))

**AI products:** see the table in section (d).

### 5. Out-of-area and third-party calls

**How it works today:**
1. A caller in Boston dials 911 and reaches the **Boston-area PSAP**, because routing follows the caller's device, not the incident.
2. That call-taker must identify the PSAP covering the incident address in LA and **warm-transfer** the call, relaying location, callback number, nature and safety information (NENA §5.3).
3. NENA §5.5.2 says neighboring PSAPs SHOULD be on single-button transfer, and that *"out-of-area PSAP contact information may be found in the NENA Enhanced PSAP Registry and Census (EPRC) or via NLETS."* **[V]**

**Tools:**
- **NENA EPRC:**
  - Search by address, intersection, lat/long or community.
  - Gives 24×7 transfer information and the priority ten-digit number.
  - Free, but only to verified government public-safety staff with individual credentials.
  - Stable release since March 2020.
  
  **[S]** ([NENA PSAP Registry](https://www.nena.org/page/PSAP_Registry_home), [GeoComm](https://www.geocomm.com/nena-eprc/))
- **FCC Master PSAP Registry:**
  - A public CSV/XLSX with FCC ID, PSAP name, state, county and city. The FCC page was updated on 22 April 2025.
  - It covers more than 8,900 primary and secondary PSAPs.
  - It appears **not to include 10-digit numbers**. **[UNVERIFIED; check the file]**
  
  **[S]** ([data.gov](https://catalog.data.gov/dataset/911-master-psap-registry), [FCC](https://www.fcc.gov/pshs/services/911-services/enhanced911/psapregistry.html))
- **Illinois** requires a directory of a 24/7 10-digit emergency number for every primary PSAP, answered by a person rather than an automated system. **[V statute]** ([50 ILCS 750/17.5](https://lig.ilga.gov/legislation/ilcs/documents/005007500K17.5.htm))
- **Commercial:** Northern911 runs an out-of-jurisdiction line that PSAPs call to have the caller transferred almost anywhere in the US or Canada. **[S vendor]** ([Northern911](https://northern911.com/public-safety/out-of-jurisdiction-support-line/))

**Known failures:**
- **Legacy transfers carry voice only**, so the caller repeats everything to the second dispatcher. In one case a Maine caller was reporting a Vermont emergency. **[V state report]** ([Maine Legislature 2015](https://lldc.mainelegislature.org/Open/Rpts/hv551_4_m2m38_2015.pdf))
- Cross-river ping-pong: in a teen's drowning in Loudoun VA, callers were bounced between VA and MD. **[S]** (NBC4)
- Each transfer costs about 21 s on average in Snohomish County, down from 51 s. **[S]**
- **In the Palisades fire, the third-party callers were the problem:** relatives far away called about people who had already evacuated, which sent officers to empty homes. **[V]** (LAPD AAR)

**Time an out-of-state transfer takes:** no measured figure was found. **[UNVERIFIED]** NENA has no specific "third-party caller" standard beyond the general rules (§5.2, §5.5.2), and none was found. **[UNVERIFIED]**

### 6. Language

- **Share of LA residents:** about 24% of LA County residents aged 5+ (2.19M of 9.28M) speak English less than "very well". 42% of Spanish speakers, and more than 50% of Korean, Chinese, Vietnamese and Khmer speakers, fall in that group. **[S]** ([LA Almanac](https://www.laalmanac.com/population/po47.php), older ACS) The current figure is in DPH Community Health Profiles (ACS 2018–22). **[UNVERIFIED value]**
- **LAPD calls:**
  - Out of 2.2M 911 calls in January–September 2023, more than **5,000 were in languages other than English or Spanish**.
  - LAPD reaches an interpreter in **up to 45 s**.
  - Non-English speakers wait in a queue when no bilingual PSR is free.
  
  **[S]** (LA Times via [AOL](https://www.aol.com/news/city-officials-call-lapd-hire-110036429.html)) LAPD's Spanish share is **not published [UNVERIFIED]**. For comparison, NYPD handled 51% of Spanish calls in-house in 2020, and Spanish made up 89% of interpreter requests in 2010. **[S]** ([NYPD Language Access Plan](https://www.nyc.gov/assets/nypd/downloads/pdf/public_information/nypd-language-access-plan-2022-August.pdf))
- **How interpreter lines work:**
  1. The call-taker conferences in a vendor line such as LanguageLine.
  2. An operator answers, sometimes after an account or billing code is entered.
  3. The language is identified and an interpreter joins a three-way call.
  
  Delays grow when codes must be entered or the language is rare. **[S]** ([MN DPS](https://dps.mn.gov/divisions/ecn/programs/911/Pages/language-integretation.aspx)) The Minnesota program averaged under 11 s to connect across 5,000+ calls in 39 languages. **[V state page]**
- **Delay added:** 49 s average to reach the interpreter, and BLS assignment 33% slower (82% slower when an interpreter was used). **[V]** (Meischke 2013) Routing through an interpreter added almost 2 min before CPR instructions began. **[S]** ([CDC stacks, J Immigrant Minority Health](https://stacks.cdc.gov/view/cdc/214457))
- **LAPD wants** *"two-way, real-time translation … [to reduce] language barrier delays and third-party hand-offs"*. **[V]** (LAPD fact sheet)

### 7. Information operators wish they had when the call starts

There is no rigorous survey ranking the fields. **[UNVERIFIED gap]** The evidence below is triangulated from the sources above:

| Information | Evidence of the need | Source |
|---|---|---|
| **Verified location** | 79% want it within 15 s, and 82% have low confidence in wireless location. NENA SHALLs read-back | **[S]** survey, **[V]** NENA §5.2.1 |
| **Callback number** | NENA requires checking it against ANI. It's needed for abandoned-call callbacks | **[V]** NENA §5.2.1, §5.4 |
| **Language** | LAPD and Pulse 2025 both name translation a top need. It adds 49 s plus 33–82% to dispatch time | **[V]** LAPD, Meischke; **[S]** Pulse |
| **Hazards** | A NENA minimum field for text calls. LAFD sent units into the fire area unaware | **[V]** NENA §4.1.3, LAFD AAR |
| **Number of people / who is involved** | A NENA minimum field for text calls ("identity of those involved and their location") | **[V]** NENA §4.1.3 |
| **Medical / mobility needs** | Palisades: many stuck callers were elderly or disabled. Eaton: two homebound men died after three calls. LAFD praised MFC for relaying special-assistance needs | **[V]** LAPD and LAFD AARs; **[S]** LAist |
| **Caller relationship and freshness ("last heard from them when?")** | Palisades calls from relatives sent officers to homes that had already been evacuated | **[V]** LAPD AAR |
| **Duplicate / existing-incident awareness** | A manual master incident was created. ULRI said 911 information didn't reach the operations chief. In Sandy most calls were duplicates | **[V]** LAPD AAR; **[S]** ULRI, Sandy |
| **"Who/what/where" summary** | LAPD's requested AI feature list | **[V]** LAPD fact sheet |

### 8. CAD fields and data standards for a pre-filled incident card

**Fields required or typical:**
- NENA §5.2: location (SHALL), plus callback number, nature and identity (SHOULD).
- NENA §4.1.3 adds time of occurrence, hazards and the people involved with their location.
- NENA §5.3 transfer relay: location, callback number, nature, known safety information. **[V]**
- FIRESCOPE's CAD-to-CAD examples: incident number, incident address, incident type, reporting party, responding units. **[S]** ([FIRESCOPE white paper](https://firescope.caloes.ca.gov/ICS%20Documents/FIRESCOPE%20Interoperability%20White%20Paper.pdf))

**Standards:**
- **APCO 2.103.2-2019, Common Incident Types for Data Exchange:** a standard incident-type code list. Agencies map their internal codes to it. **[S]** ([APCO](https://www.apcointl.org/standards/common-incident-types-for-data-exchange))
- **APCO 1.110.1-2015:** minimum CAD functional requirements.
- **APCO 1.111.2-2018:** disposition codes.
- **APCO 1.116.2-2020:** status codes. **[S]**
- **APCO/NENA 2.105.1-2017 EIDD**, the Emergency Incident Data Document: the predecessor of EIDO. **[S]**
- **NENA EIDO (NENA-STA-021):**
  - A JSON object for sharing incident information between NG911 systems, carrying hundreds of NIEM elements.
  - It holds incident identifiers, **linked calls**, location, incident type, notes, responding units, status, and the people and vehicles involved.
  - A conveyance standard was published in 2025.
  - The exact document number and component names are **[UNVERIFIED]**. Sources cite both STA-021 and STA-024.1.1-2025. The NENA KB returned 403.
  
  **[S]** ([NENA KB EIDO](https://kb.nena.org/wiki/EIDO_(Emergency_Incident_Data_Object)), [NENA release](https://www.nena.org/news/584569/NENA-Releases-ANSI-Approved-Emergency-Incident-Data-Object-EIDO-Standard.htm), [NENA FAQ](https://kb.nena.org/wiki/EIDO_%26_IDX_FAQ_(Frequently_Asked_Questions)?oldid=3588))
- **NENA-STA-012 / IETF RFC 7852, Additional Data:**
  - It has three kinds of data: for the Call, the Caller and the Location.
  - RFC 7852 defines the blocks **ProviderInfo, ServiceInfo** (environment, type, mobility), **DeviceInfo, SubscriberInfo** (an xCard) and **Comment**.
  
  **[V]** ([RFC 7852](https://www.rfc-editor.org/rfc/rfc7852.html)); **[S]** ([NENA KB](https://kb.nena.org/wiki/Additional_Data?oldid=4823))

**Proposed DIZA "incident card"** (field names follow EIDO concepts, and incident types use APCO 2.103 *suggestions* only):

```
incident_card:
  card_id, created_at, source: "DIZA-intake", status: "draft-unreviewed"
  call:      ani, callback_confirmed (bool), alt_callback, language_detected, interpreter_needed
  caller:    name, relationship (self | on-scene witness | remote family/friend | other),
             on_scene (bool), last_contact_with_subject (time, for remote callers)
  location:  spoken_text, read_back_confirmed (bool), geocode {lat, lon, accuracy_m, method:
             spoken | sms-gps | device}, in_jurisdiction_psap (suggested), cross_street/landmark, unit/floor
  nature:    caller_words_verbatim, time_of_occurrence, suggested_incident_type (APCO 2.103, flagged as suggestion)
  safety:    hazards [fire, smoke, water, weapons, downed lines], people_count, trapped (y/n/unknown),
             mobility_or_medical_needs (free text)
  linkage:   possible_duplicates [{incident_id, distance_m, similar_calls}]   # flag only, never merge
  comment:   free text (RFC 7852 Comment)
  audit:     transcript_ref, fields_verified_by_human (filled at pickup)
```

---

## (d) What competitors already do

| Product | What it does | Where deployed | Reported results | Overlap with "queue-time intake card"? | Source |
|---|---|---|---|---|---|
| **Aurelian** ("Ava", "AI Annie") | Voice AI on **non-emergency** lines. Triages noise/parking/lost-wallet calls, collects details, creates a report or relays to police, and transfers real emergencies to a human. Gives an audit trail | 12+ centers by Aug 2025 (Snohomish WA, Chattanooga TN, Kalamazoo MI, Bonneville/Idaho Falls ID). El Cajon PD from 1 Jul 2026 (about $74k/yr) | $14M Series A (NEA). Volusia SO: 98.5% "successful resolution". About 3 h saved per operator per day. Halved backlog in Snohomish. All vendor/agency claims | Non-emergency only. Does not touch the 911 queue | **[S]** [TechCrunch](https://techcrunch.com/2025/08/27/911-centers-are-so-understaffed-theyre-turning-to-ai-to-answer-calls), [Idaho Falls](https://idahofallsidaho.gov/CivicAlerts.aspx?AID=2859), [Hoodline](https://hoodline.com/2026/07/hold-music-who-el-cajon-puts-ai-on-the-line-for-non-emergency-police-calls/) |
| **Hyper** (Motorola Solutions, acquired 9 Apr 2026) | Agentic voice AI for non-emergency/311 calls. Answers every call at once, offers Spanish, transfers, sends texts and links, and escalates to the 911 queue. Motorola plans "Assist Agents" for language barriers and guidance | San Diego County SO (Mar 2026, 24/7), La Mesa PD | SDSO non-emergency waits about **halved**. Hyper answers up to 20% of about 2,000 non-emergency calls a day | Non-emergency only | **[V vendor PR]** [Motorola](https://www.motorolasolutions.com/newsroom/press-releases/hyper-acquisition-and-new-agentic-assist-agents.html); **[S]** [Police1](https://www.police1.com/innovation-report/how-san-diego-county-uses-ai-to-answer-non-emergency-calls-and-support-911-dispatchers) |
| **Prepared / Axon 911** (Axon announced the deal 23 Sep 2025) | **In-call** assist: real-time transcription, key-detail extraction (names, locations, vehicles, weapons), translation (70+ languages), **summary pushed to CAD before the call ends**, 100% QA, radio monitoring, non-emergency triage. Axon "Ashley" AI is used on non-emergency lines | 1,000+ agencies in 49 states. A 2026 report lists LAPD, SDPD, Stockton and others. Boulder PD "Ashley" from late Oct 2026 | Vendor: −66% call processing time, −50% non-emergency calls (no independent source) | **Closest.** But it starts *after* a human answers, and nothing is captured while the caller waits | **[S vendor]** [Prepared blog](https://prepared911.com/blog/axon-911-intelligence-that-starts-the-moment-a-call-is-answered), [AWS listing](https://aws.amazon.com/marketplace/pp/prodview-v6x5yk45x7ebm), [Contra Costa News](https://contracosta.news/2026/03/23/antioch-police-seek-ai-powered-911-dispatch-software/) |
| **Carbyne APEX** | Cloud call handling. AI two-way translation (detects the language in seconds; claims up to 70% faster than a human interpreter), AI-V Emergency Call Triage, AI-V Admin Assist (non-emergency), c-Lite location/video links | Various PSAPs (e.g., Orleans Parish) | Vendor claims only | In-call. The translation overlaps with ours | **[S vendor]** [Carbyne AI](https://carbyne.com/solutions/ai-that-works-for-you), [translation PR](https://carbyne.com/resources/press/carbynes-apex-emergency-call-handling-system-now-offers-ai-driven-two-way-translation-capabilities-to-improve-9-1-1-response-time-and-accuracy/) |
| **RapidSOS Harmony / UNITE** | "AI co-pilot" that combines data feeds (device location, alarms, IoT, vehicles) into one incident view inside CAD/CPE and automates alarm-call steps | Agencies using RapidSOS (free portal); Harmony needs Digital Alerts | Vendor claims | Data fusion, not caller intake | **[S]** [Police1](https://www.police1.com/police-products/communications/rapidsos-introduces-harmony-the-first-ai-co-pilot-for-911) |
| **Corti** | Listens to EMS calls and flags out-of-hospital cardiac arrest | Copenhagen EMS (claimed) | Small study: detected 93–95% vs 73% for dispatchers, in about 48 s, with 2% false positives. Results of the larger 170k-call study weren't checked | Decision support in the call. A clinical signal, not intake | **[S]** [WEF](https://weforum.org/stories/2018/06/this-ai-detects-cardiac-arrests-during-emergency-calls), [Bloomberg](https://prod.cm.bloomberg.com/news/articles/2018-06-20/the-ai-that-spots-heart-attacks) |
| **Northern911** | Human out-of-jurisdiction transfer line for PSAPs (US/Canada) | Subscribing ECCs | — | Out-of-area routing, human-run | **[S vendor]** [Northern911](https://northern911.com/public-safety/out-of-jurisdiction-support-line/) |
| **LanguageLine and similar** | Human interpreters conferenced into calls | Most PSAPs | 11–49 s to connect (see §6) | We pre-detect the language. We don't replace interpreters | §6 |

**Gap we can claim, worded carefully:**
- Every deployed AI voice agent we found works on **non-emergency lines**.
- Every in-call 911 assistant we found starts **after a human answers**.
- We found **no product that turns the 911 hold-queue wait into verified intake**: location read-back, callback number, language, caller relationship and duplicate flag, delivered as a card at pickup.

This is **[UNVERIFIED]**: we may have missed one, so say "we found none". It also runs into NENA's expectation that a human answers 911, so present it as **surge/overflow-only and approved by policy**.

---

## (e) Recommended problem statement for the hackathon

> **During a wildfire surge in Los Angeles, 911 call-takers lose minutes they don't have, and units are sent to empty homes, because every caller reaches a human with nothing captured. The location isn't verified, the language is unknown, and nobody knows whether the caller is on scene or a relative far away asking about someone already reported or evacuated. Today they re-ask everything from scratch after a hold that, on a normal 2024 day, missed the 15-second standard for 43% of calls. They conference an interpreter (49 s on average) and group duplicate calls by hand into a "master incident".**

**Evidence behind each clause:**
- LAPD answered only 57.43% of calls within 15 s (2024). **[V]**
- 160+ Palisades evacuation calls, many for people already evacuated, came from relatives, and a manual master incident was created. **[V]**
- LAFD dispatched into the fire area unaware of it. **[V]**
- Interpreter connection takes 49 s on average. **[V]**
- LAPD wants AI as *"a tool for PSRs … not an automated call-taking service"*. **[V]**

**One-line version for the slide:** *"During disasters, LA 911 call-takers waste the first minute of every call re-asking 'where, who, what language, is this a new incident?', and relatives' duplicate calls send units to empty homes. DIZA gathers and verifies those facts while callers wait in the queue and hands the call-taker a card. It never decides."*

---

## 9. The January 2025 LA fire communication failures, checked against primary sources

**Primary documents read in full text for this section:**
- **McChrystal AAR:** McChrystal Group, *After-Action Review of Alert Notification Systems and Evacuation Policies for the Eaton and Palisades Fires* (LA County, Sept 2025). [Full report PDF](https://file.lacounty.gov/SDSInter/bos/supdocs/207915.pdf)
- **Amendment #1 (May 2026).** [PDF](https://file.lacounty.gov/SDSInter/lac/1208709_Amendment1toAAR-May2026.pdf)
- **Eaton synopsis:** the County's Eaton synopsis and timeline. [Synopsis](https://file.lacounty.gov/SDSInter/lac/1192777_AAR_EatonFireSynopsisofFindingsandTimeline.pdf), [Timeline](https://file.lacounty.gov/SDSInter/lac/1191567_EatonFireTimelineOverview.pdf)
- **Citygate report:** Citygate Associates, *Investigation Report of the Eaton Fire Evacuation Alerts* (updated 18 May 2026). [PDF](https://file.lacounty.gov/SDSInter/lac/1208708_InvestigationReportoftheEatonFireEvacuationAlerts_05-18-26_.pdf)
- **County actions memo.** [PDF](https://file.lacounty.gov/SDSInter/lac/1192779_AAR_SummaryofCountyActionsandImprovements.pdf)
- **LAPD AAR and LAFD AAR** (both linked above).

All of these are listed on [lacounty.gov/aar](https://lacounty.gov/aar/).

**Not read directly:** the UL Research Institutes (ULRI/FSRI) 724-page report and the LA Times 911-log reporting. Both are **[S]** through news coverage.

### 9(a) Evacuation alert timing: west Altadena (Eaton) vs fire and 911 reports

All times are from January 7–8, 2025.

| Time | Event | Source |
|---|---|---|
| 6:13 pm | LASD gets the first call about a possible brush fire in Eaton Canyon. LACoFD gets its own call at 6:17 pm | **[V]** McChrystal AAR p.13–14 |
| 6:23 pm | **Watch Duty publicly reports the fire** | **[V]** McChrystal AAR p.14; Timeline |
| 6:45 pm | All aircraft grounded by wind (about 30 min after mobilization), so there's no aerial situational awareness | **[V]** Synopsis |
| 6:48 pm | First advisory ("BE ALERT AND MONITOR") goes to 12 zones | **[V]** Synopsis |
| 7:26 pm | First evacuation orders (7 zones). By 9:00 pm 11 more zones, and by 10:30 pm 16 more | **[V]** Synopsis |
| about 10:15 pm | **LACoFD dispatch begins forwarding information from 911 calls in the Eaton area to Operations, *"as there were no other response resources available to directly dispatch into that area"*** | **[V]** Citygate §2.2, p.23 |
| 10:50 pm | **First 911 reports of fire west of Lake Ave.** None of those 911 locations appear in CAL FIRE damage (DINS) reports. One cited address, "512 Calaveras Street", *"was not an official street or house number"* | **[V]** McChrystal AAR p.26 |
| 11:23–11:32 pm | Field-to-Unified Command call and texts. The amendment and Citygate say these concerned **Sierra Madre** zones, not "Altadena to La Cañada" as first reported | **[V]** Amendment #1; Citygate Findings #9–10 |
| 12:55 am | **First validated structure fire west of Lake** (500 block E Las Flores Dr), reported by an LASD deputy. A deputy also requested help with an evacuation at 6xx E Sacramento St (west of Lake). Radio traffic at 12:57 am | **[V]** McChrystal AAR p.26; Citygate timeline p.33 |
| 1:12–3:00 am | **OEM got no direction from LACoFD or LASD to send any Eaton alerts** | **[V]** McChrystal AAR p.26 |
| 2:18 am | Field radio: fire front moving west along the foothills above Lake Ave. Incident Command starts evaluating zones west of Lake | **[V]** McChrystal AAR p.17; Citygate Finding #17 |
| about 3:00 am | Incident Command directs OEM | **[V]** |
| **3:25 am** | **First evacuation alert covering west of Lake Ave** (1 order covering 13 zones, plus 1 warning covering 6 zones) | **[V]** McChrystal AAR p.26; Timeline |
| 4:35, 5:15, 5:42 am | More orders (23, 19 and 5 zones). The Calaveras pocket only got its order at 5:42 am **[S]** | **[V]** Timeline; **[S]** [LA Times via Yahoo](https://www.yahoo.com/news/waited-waited-evacuation-order-fire-110014553.html) |
| after 5:00 am | FireGuard satellite: the **fire front** crossed Lake Ave only after 5 am, but **spot fires hit west Altadena earlier** | **[V]** McChrystal AAR p.17 |

**Measured gaps:**
- From the first (unvalidated) 911 reports west of Lake to the alert: **about 4 h 35 min** (10:50 pm to 3:25 am).
- From the first validated structure fire and deputy request to the alert: **about 2 h 30 min** (12:55 am to 3:25 am).
- From the field radio to the alert: **67 min** (2:18 am to 3:25 am).

**Official conclusions:**
- **McChrystal:** *"no single point of failure"*, but *"a series of weaknesses"*. Evacuation decisions *"could not keep pace with the fire"*. Many neighborhoods west of Lake got no warning before residents decided to leave. **[V]**
- **Citygate:** orders were *not delayed* by Unified Command. It found Incident Command was *"still blind"* to fire movement at about 1:00 am (Finding #14). **[V]**

**Deaths:** news reports say almost all Eaton deaths were west of Lake: "18 of the 19" per Fire Engineering, and "all 17" per an earlier LA Times count. **[S]** ([Fire Engineering](https://www.fireengineering.com/firefighting/wildland-firefighting/eaton-fire-no-misconduct-delay-in-evacuation-notices-to-west-altadena-ca-report-says/), [LA Times via Yahoo](https://www.yahoo.com/news/17-deaths-eaton-fire-were-024433120.html))

**ULRI:** if 911 calls had been routed through the Operations Section Chief, the information west of Lake *"could have been known and acted upon earlier."* **[S]** ([Firehouse/LA Times, Oct 2026](https://www.firehouse.com/operations-training/wildland/news/55409515/chaos-missteps-at-palisades-eaton-fires-found-during-ul-fsri-probe))

**Palisades:** the AP found homes were already burning and roads jammed when the evacuation order came. **[S]** ([AP via Click2Houston](https://www.click2houston.com/news/national/2025/01/17/homes-were-burning-and-roads-already-jammed-when-pacific-palisades-evacuation-order-came-ap-finds/)) The detailed Palisades alert timeline is in the McChrystal AAR pp.21–25 but was not extracted here. **[UNVERIFIED detail]**

### 9(b) Did 911 calls or ground reports from west Altadena exist before the order?

**Yes.**
- 911 reports of fire west of Lake existed **from 10:50 pm**. McChrystal judged them unvalidated against the DINS damage data.
- A deputy's report of a house on fire west of Lake came at **12:55 am**, along with a deputy's evacuation-assistance request west of Lake. Radio traffic came at 12:57 am, and structure fires near upper Lake Ave were reported at 1:30 am (Citygate timeline).

All **[V]**.

**Call counts:**
- The McChrystal AAR plots *"911 LAC Fire Dispatch calls for structure fires by time interval"* (Appendix 11, Figures 35–36, 39). These are images, so we counted the dots by eye on PDF page 122 (Figure 36, Eaton). **[EST, visual count]**
  - In the **6:00 pm–12:30 am** panel, about 2 red dots (structure-fire 911 calls) and 3 blue dots (calls whose addresses were not damaged or not in DINS) sit in **unshaded zones west of the ordered area**.
  - In the **12:30–3:00 am** panel, **about 10 (±3) red structure-fire 911 calls cluster in unshaded northwest Altadena zones** (no order or warning shown), before the 3:25 am alert.
  - The figure doesn't say whether shading shows zone status at the start or end of each interval, so treat this as indicative only. Exact counts need the source data.
- McChrystal also notes *"multiple calls in the LACoFD's dispatch records for houses on fire or people trapped in burning homes that were not on the DINS reports."* In other words, **911 reports were real but noisy**. **[V]**
- The LA Times reported from 911 logs that deputies evacuated a west Altadena resident just after 11:30 pm. **[S/UNVERIFIED]** The search snippet was garbled, so we haven't confirmed it.

### 9(c) Cell and power outages that affected 911 and alerts

- **McChrystal AAR [V]:**
  - Public Safety Power Shutoffs (PSPS) started at 3:40 pm on January 7 (Timeline). Maps of de-energized circuits are in Appendix 8.
  - The report says alert systems rely on *"adequate cellular, radio, and Wi-Fi signals … and, most importantly, commercial power."* PSPS can shut off cell towers, fire can destroy them, and smoke degrades the signal.
  - *"In some neighborhoods, automated call systems failed to operate due to the loss of electricity"*.
  - Under these conditions *"the only reliable redundancy"* is door-knocking and loudspeakers (pp.48–51).
  - Exact figures for towers out are **not given [UNVERIFIED]**.
- **Citygate [V]:** power was *"highly likely … still on in many neighborhoods in Altadena"*. Many early fires ahead of the front were started by downed power lines rather than embers (Finding #12).
- **LAPD AAR (Palisades) [V]:**
  - Cell networks were *"down, or overburdened"*, so relatives called 911.
  - DWP shut down the Green Mountain radio repeater at 4:20 pm, and FirstNet *"could not provide consistent connectivity"* in Malibu.
  - Service was restored with SatCOLT/COW trailers and new Verizon and AT&T towers.
- **ULRI:** police dispatchers routed 911 calls through a captain's personal cellphone. **[S]** (NBC News)

### 9(d) LAFD/LAPD unified command breakdowns

- **LAPD AAR [V], pp.40–41:**
  - *"coordination between LAPD and LAFD was poor … Though both agencies were co-located at the same CP, the two departments did not collectively establish a unified command structure or identify shared objectives."*
  - There was no chronological log, and officer counts didn't match the ICS 211 forms, which *"resulted in diminished situational awareness."*
  - The command post moved 3 times on day 1, and three separate UCP sites were used before Cal Fire's Zuma Beach UCP opened on 8 January.
  - The tactical alert came 45 min after the first calls.
- **LAFD AAR [V]:**
  - Metro Fire Communications didn't follow the ICS-205 communications plan and couldn't transmit on VHF.
  - Move-up companies went unaccounted for for hours.
  - MFC dispatched units into the fire area unaware of it.
- **ULRI:** *"up to 26 units deployed without the knowledge of incident command"* (Palisades). **[S]**
- **Eaton (McChrystal) [V]:** *"It does not appear that LASD staff were always initially aware in real time of what zones were designated"* by Unified Command, even though they were co-located at the ICP (p.81). Zone decisions travelled to OEM by phone call or text before being entered in Genasys EVAC.

### 9(e) Residents relying on Watch Duty and social media

- **McChrystal AAR [V]:**
  - Watch Duty reported the Palisades fire at 10:33 am (relaying the AlertCalifornia camera) and the Eaton fire at 6:23 pm.
  - *"Some residents said that they relied on third-party apps, such as WatchDuty, or social media for updates; some were alerted by neighbors or family … there was no clearly recognized, centralized source of accurate information."*
  - Social media also hurt: the trending phrase *"The fire is moving east"* *"fostered some complacency"* west of Lake (Synopsis).
  - WEA and EAS alerts are what update third-party apps such as Watch Duty (p.~88).
- **Usage:**
  - More than 600,000 new users in 24 hours, briefly the #1 App Store download, and about 7.2M users at the end of 2024. **[S]** ([PopSci](https://www.popsci.com/environment/watch-duty-wildfires/))
  - "Over a million downloads in 24 h" was also reported. **[S]** ([ABC7](https://abc7news.com/post/watch-duty-app-founded-bay-area-sees-record-downloads-socal-fire-information/15784521/))
  - The number of LA-specific users is **[UNVERIFIED]**.

### 9(f) The "38-year-old network" claim

- **Verified, with a correction: it's a dispatch system, not a "network".** The McChrystal AAR (p.30) lists among LASD's pre-incident challenges *"the recurring failure of its 38-year-old computer-aided dispatch (CAD) system."* **[V]**
- The system crashed on New Year's Eve 2024, was patched just before the fires, and crashed again about a month later. **[S]** ([CBS LA](https://www.cbsnews.com/losangeles/news/la-county-sheriffs-departments-dispatch-system-crashes-again))
- The County memo says LASD is testing a new CAD (expected late 2025 or early 2026). LACoFD is contracting for a new CAD that *"relays 911 call information to incident commanders more quickly"*, and LASD launched a "Citizen Evacuation Tracker" in April 2025. **[V]** (County actions memo)
- ULRI/NBC: LASD is replacing the 38-year-old system and adding 80 dispatchers. **[S]**
- Don't call it the "911 network". The 911 network itself (Cal OES / NG911) is a separate system. **[V by absence: no source says the 911 network is 38 years old]**

### Which of these failures an intake and clustering tool could plausibly shorten, and which it can't

The tool we have in mind:
- AI gathers and verifies caller reports.
- Deterministic clustering shows a human something like *"N independent callers report fire in zone X; no evacuation order yet"*.
- The human approves any alert.

**What it could plausibly shorten:**
- **The 10:50 pm → 3:25 am signal-to-decision gap in west Altadena.** The 911 reports existed, and Citygate shows dispatch was already forwarding 911 information to Operations with no units to send. The information didn't reach the alert decision as a *zone-level, corroborated* signal. Incident Command was "blind" from the air, OEM got no direction between 1:12 and 3:00 am, and ULRI says the information could have been acted on earlier if routed to Operations.
- A cluster view counting independent callers per Genasys zone, with a flag such as **"zones with ≥N reports and no active order"**, is exactly the missing artifact. It could have surfaced the 12:55 am deputy report together with the earlier 911 calls about two hours sooner, as a *prompt for a human*.
- **Noisy reports and duplicate third-party calls.** Records include invalid addresses ("512 Calaveras") and LAPD calls about people who had already evacuated. Address read-back, a caller-relationship field (on scene vs remote relative) and "independent caller" counting reduce false clusters. McChrystal's own caution means the tool must *show corroboration and uncertainty*, not assert that a fire exists.
- **Zone-awareness gaps between agencies.** LASD didn't always know which zones were ordered, and MFC dispatched into the burn area. Overlaying active orders on the same map as incoming reports addresses this.

**What it can't reach:**
- Destroyed or de-energized cell towers, PSPS, the Green Mountain repeater, VHF/LMR interoperability, FirstNet gaps, and grounded aircraft.
- The absent unified command structure and its documentation discipline. That's an ICS training problem.
- The 38-year-old CAD replacement.
- Residents who never receive an alert because their phones have no power or signal. McChrystal says only door-knocks work then.
- The judgement call itself, including the county's stated worry about over-warning.

**Two dependencies:** the tool only helps if (1) callers can still reach a line, so it's no help where towers are down, and (2) an agency actually puts the cluster view in front of the alert decision-maker (the OEM A-Rep or Operations). That second point is an adoption question, not a technical one. **[EST, our assessment, not from a source]**

---

## Not verified / open items
- Exact counts of 911 structure-fire calls by time interval for Eaton and Palisades (McChrystal AAR Appendix 11, pp.120–124). We only have a visual estimate for Eaton (§9b).
- Full text of the ULRI/FSRI report.
- LA Times 911-log details (the 11:30 pm deputy evacuation).
- Number of cell sites out during the fires.
- A national median for call processing time, and the time location verification takes. Neither was found. FPRF averages only.
- What makes up LAPD's ~547k gap between calls received and answered in 2024.
- 911 wait times and abandonment counts for LAPD, LAFD, LASD and Pasadena during 7–9 January 2025. None are published in the AARs we read. A CPRA request is needed.
- The Maui County AAR returned 403. Its figures come from news summaries.
- EIDO document number and component names (STA-021 vs STA-024.1.1-2025).
- Whether the FCC PSAP Registry includes 10-digit numbers.
- LAPD's Spanish share and its interpreter vendor.
- Current wireless location accuracy rates (post-2018 hybrid location).
- Any NENA guidance specific to third-party or remote callers.
- Whether any vendor already does 911 queue-time intake.
- Whether agency policy or state law (Cal OES) would allow an automated pre-answer on 911 lines. **This must be checked before claiming the use case. It is the biggest risk to this framing.**
