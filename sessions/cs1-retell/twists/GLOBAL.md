# Twist 2 research: DIZA in other countries (checked 2026-10-17; items marked (unverified) and the list at the end need checking before presenting)


## 1. Country table

Retell codes come from docs.retellai.com/build/language-support. Retell has **no** Telugu, Bengali, Yoruba, Hausa or Igbo, and no separate Mexico Spanish code (use `es-419`).

| Country | Emergency | Crisis line | Languages (Retell code) | Alert system | Privacy law |
|---|---|---|---|---|---|
| China | 110 police, 119 fire, 120 ambulance, 122 traffic | **12356**, the national psychological-assistance hotline (NHC; live in all 31 provinces by 1 May 2025) | Mandarin `zh-CN`, Cantonese `yue-CN` | National Emergency Early Warning Information Release System (国家突发事件预警信息发布系统) (name unverified) | PIPL (2021) + Cybersecurity Law + Data Security Law |
| Japan | 110 police, 119 fire/ambulance, 118 coast guard | Kokoro no Kenko Sodan Dial 0570-064-556 (MHLW); Inochi no Denwa 0570-783-556 (unverified this session) | Japanese `ja-JP` | J-Alert + Emergency Alert Mail (cell broadcast) | APPI |
| South Korea | 112 police, 119 fire/ambulance | **109**, the MOHW 24h suicide-prevention line (since Jan 2024; being made an emergency number from Oct 2026) | Korean `ko-KR` | Emergency disaster text (재난문자, CBS) | PIPA |
| Philippines | 911 | NCMH Crisis Hotline **1553** (toll-free landline), 0919-057-1553 / 0917-899-8727 | Filipino `fil-PH` (ASR via Azure only), English `en-US` | ECBS (RA 10639, Free Mobile Disaster Alerts Act) | Data Privacy Act 2012 (RA 10173) |
| Mexico | 911 | Línea de la Vida 800 911 2000 (unverified this session) | Spanish `es-419` | SASMEX (quake early warning) + cell-broadcast alerts (national drill reached phones Sept 2025) | **New** LFPDPPP (DOF 20 Mar 2025, replaced the 2010 law). INAI was dissolved; the regulator is now the Secretaría Anticorrupción y Buen Gobierno |
| India | 112 (ERSS); legacy 100/101/102/108 | Tele-MANAS **14416** / 1-800-891-4416 (unverified this session) | Hindi `hi-IN`, English `en-IN`, Tamil `ta-IN`, Marathi `mr-IN` | NDMA **SACHET** (CAP-based SMS, all 36 states/UTs). Cell broadcast launched and tested May 2026 | DPDP Act 2023 + DPDP Rules (notified 13 Nov 2025, phased in; core duties ~May 2027) |
| United Kingdom | 999 or 112 | Samaritans **116 123** | English `en-GB` | UK Emergency Alerts (cell broadcast) | UK GDPR + DPA 2018 (amended by the Data (Use and Access) Act 2025) (unverified this session) |
| Germany (EU) | 112 fire/ambulance, 110 police | TelefonSeelsorge 0800 111 0 111 / 0800 111 0 222 / 116 123 | German `de-DE` | Cell Broadcast (DE-Alert/EU-Alert) + NINA app + MoWaS | EU GDPR + BDSG |
| Australia | 000 (112 from mobiles) | Lifeline **13 11 14** | English `en-AU` | Emergency Alert (SMS/voice). It is being replaced by **AusAlert** cell broadcast (planned Oct 2026; old system ends by Jul 2027) | Privacy Act 1988 (amended 2024) |
| Brazil | 190 police, 192 SAMU ambulance, 193 fire | CVV **188** | Portuguese `pt-BR` | **Defesa Civil Alerta** (cell broadcast) + SMS 40199 (opt-in by CEP) | LGPD (Lei 13.709/2018) |
| Kenya | 999 / 112 | No government line found. Befrienders Kenya +254 722 178 177 (unverified) | Swahili `sw-KE` (TTS: Fish/ElevenLabs/OpenAI only), English `en-US` | No cell broadcast yet. Government SMS via operators (CA order, Oct 2026). CBS readiness assessment underway | Data Protection Act 2019 |
| Nigeria | 112 | No government line found. SURPIN 0800 078 7746 (unverified) | English only (`en-US`). Yoruba, Hausa and Igbo are **not supported** | No national cell broadcast found (unverified) | Nigeria Data Protection Act 2023 |

## 2. Retell telephony outside the US

- **Buying numbers:** "Currently we only support purchase of US and Canada numbers." Twilio covers US, US toll-free and Canada. Telnyx covers US only. ([purchase-number](https://docs.retellai.com/deploy/purchase-number))
- **Calling abroad with Retell numbers** ([international-call](https://docs.retellai.com/deploy/international-call)):
  - **Twilio:** India, Australia, Germany, Spain, UK, Mexico, France, Japan, Canada, Italy, Indonesia, Philippines, Malaysia, Thailand. Rates run from $0.03/min (Canada) to $0.80/min (Philippines).
  - **Telnyx:** India, Canada.
  - **Not on the list:** China, Korea, Brazil, Kenya and Nigeria.
- **Local numbers abroad, bring your own** ([custom-telephony](https://docs.retellai.com/deploy/custom-telephony), [twilio](https://docs.retellai.com/deploy/twilio), [telnyx](https://docs.retellai.com/deploy/telnyx)):
  1. **Elastic SIP trunk (recommended).** Buy a local number from Twilio, Telnyx, Vonage or a local carrier. Point origination to `sip:sip.retellai.com`, then import the number into Retell with the carrier's termination URI. Codecs: PCMU, PCMA, G.722. Transport: TCP, UDP, TLS or mTLS, with SRTP.
  2. **Dial to SIP URI.** Register the call by API, then dial `sip:{call_id}@sip.retellai.com`. With this option, Retell's transfer feature does not work.
  3. **Twilio international outbound** needs that country enabled in Twilio's Voice Geographic Permissions.
- **Implication for DIZA:** for each country, get a local DID through a carrier that has local regulatory approval, trunk it to Retell, and handle emergency numbers through warm transfer or by telling the caller to dial them (an AI cannot place calls to 112/911 itself).

## 3. China specifics (brief)

- **Laws:** PIPL, the Cybersecurity Law and the Data Security Law apply.
  - Critical-information-infrastructure operators, and anyone above the volume thresholds, must store data locally.
  - Exports go through a CAC security assessment, a standard contract or a certification.
  - Under the CAC *Provisions on Promoting and Regulating Cross-Border Data Flows* (22 Mar 2024):
    - Security assessment: more than 1M people's personal information, or more than 10k people's sensitive personal information, per year.
    - Standard contract or certification: 100k to 1M people.
    - Exempt: under 100k people with no sensitive data.
  - Voice recordings tied to crisis or health topics are likely **sensitive** personal information, so the exemption would not apply.
- **Telecom licensing:** PSTN numbers and voice services need MIIT licences. Basic telecom requires Chinese control, and foreign ownership of value-added telecom is capped (unverified detail). A US company cannot simply buy Chinese DIDs and route them to US servers.
- **Generative AI:** public-facing LLM services need a CAC filing under the *Interim Measures for Generative AI Services* (2023). Foreign LLM APIs (OpenAI, Anthropic) are not offered in mainland China.
- **Technical:** Retell cannot sell Chinese numbers or call China. Cross-border media latency and network filtering also make real-time voice unreliable.
- **Realistic deployment:** a Chinese partner hosts everything in-country:
  - Telephony from China Telecom, Unicom or Mobile, or a licensed CPaaS such as Alibaba Cloud or Tencent Cloud voice.
  - Hosting in a mainland cloud region.
  - A registered domestic LLM (e.g. Qwen, DeepSeek, ERNIE) and domestic ASR/TTS.
  - Data stays in China. The US team shares only the design, prompts and triage logic.
  - Crisis routing goes to **12356**, and emergencies to 110/119/120.

## Sources
- Retell: https://docs.retellai.com/build/language-support · /agent/language · /deploy/purchase-number · /deploy/international-call · /deploy/custom-telephony · /deploy/twilio · /deploy/telnyx
- China 12356: https://www.news.cn/politics/20250508/b45e439c15bb4732858ad5c7640e9ba9/c.html · cross-border data flow summary: https://www.hankunlaw.com/upload/portal/20240422/03212c0c73099e85d33a605def4f6571.pdf · CAC: https://www.cac.gov.cn
- Korea 109: https://www.koreaherald.com/article/10759801
- Mexico LFPDPPP 2025: https://www.hoganlovells.com/es/publications/mexicos-new-federal-data-protection-law-what-it-means-for-companies
- India DPDP Rules: https://www.mondaq.com/india/data-protection/1708164/digital-personal-data-protection-rules-2025-notified · SACHET/cell broadcast: https://informatics.nic.in/files/websites/april-2026/india-launches-nationwide-cell-broadcast-system-for-disaster-alerts.php
- Australia AusAlert: https://www.ausalert.gov.au/node/9 · https://minister.homeaffairs.gov.au/KristyMcBain/Pages/ausalert-to-start-national-testing-this-year.aspx
- Brazil: https://estado.rs.gov.br/como-se-cadastrar-para-receber-avisos-e-alertas-da-defesa-civil-no-celular · https://cvv.org.br
- Philippines NCMH: https://tribune.net.ph/2026/01/03/doh-mental-health-hotline-gets-nearly-1k-calls-during-holiday-season
- Kenya CA/CBS: https://ca.go.ke/node/950 · https://tech-ish.com/2026/10/05/telcos-must-send-government-emergency-texts-to-all-phone-users-even-those-who-opted-out/
- Crisis-line directory (Kenya/Nigeria): https://en.wikipedia.org/wiki/List_of_suicide_crisis_lines
- Other lines (well-established, not re-fetched this session): https://www.samaritans.org · https://www.telefonseelsorge.de · https://www.lifeline.org.au · https://www.gob.mx/salud/conadic · https://telemanas.mohfw.gov.in · https://www.mhlw.go.jp

## Not re-checked this session
Emergency numbers for all 12 countries; Samaritans, TelefonSeelsorge, Lifeline Australia and CVV numbers; alert-system names for Japan, Korea, UK, Germany, Philippines; most privacy-law names (Mexico and India were checked); China telecom licensing and generative-AI filing.

## What changed in the build for this twist
Prompts no longer hard-code US numbers: `{{emergency_number}}`, `{{crisis_line_name}}`, `{{crisis_line_spoken}}`, `{{info_line}}`, `{{service_area}}`, `{{crisis_line_note}}` (US defaults: 911, 988, 2-1-1, Los Angeles). A region is a set of these values, passed per call by the inbound webhook or set as defaults for a regional deployment.
