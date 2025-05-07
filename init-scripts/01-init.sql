-- Initial database setup script
-- This script creates the core documents table and inserts sample medical documents
-- This should run first before any other initialization scripts

-- Create the documents table if it doesn't exist
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL
);

-- Insert some sample medical documents
INSERT INTO documents (title, content) VALUES
    ('SOAP Note - Annual Physical', 'Patient: patient--001

S: Pt presents today for annual physical check-up. No chief complaints. Reports generally good health, denies chest pain, SOB, HA, dizziness. Family hx of elevated cholesterol (dad), no significant personal PMH issues reported. States routine exercise (~2x/wk), balanced diet but with occasional fast-food. Denies tobacco use, reports occasional ETOH socially.

O:
Vitals:
BP: 128/82 mmHg
HR: 72 bpm, regular
RR: 16 breaths/min
Temp: 98.2°F oral
Ht: 5''10", Wt: 192 lbs, BMI: 27.5 (overweight)
General appearance: Alert, NAD, pleasant and cooperative.
Skin: Clear, normal moisture/turgor
HEENT: PERRLA, EOMI, no scleral icterus. Oral mucosa moist, throat clear, no erythema
CV: Regular rate & rhythm, no murmurs, rubs or gallops
Lungs: CTA bilaterally, no wheezing or crackles
ABD: Soft, NT/ND, bowel sounds normal
Neuro: CN II-XII intact, normal strength & sensation bilat
EXT: No edema, pulses +2 bilaterally
Labs ordered: CBC, CMP, Lipid panel

A:
Adult annual health exam, generally healthy
Possible overweight (BMI 27.5), recommend lifestyle modifications
Family hx of hyperlipidemia, screening initiated

P:
Advised pt on healthier diet, increasing weekly exercise frequency to at least 3-4 times/week
Scheduled follow-up visit to review lab results and cholesterol levels in approx. 5 months
Routine annual influenza vaccine administered today - tolerated well
No Rx prescribed at this visit.

Signed:
Dr. Mark Reynolds, MD
Internal Medicine'),
('SOAP Note - Encounter Date: 2024-06-20 (Physical Therapy Appointment)', 'Patient: Emily Williams - DOB 1996-12-02
S:
Pt returns for initial PT appt. approx. 6 months post left knee arthroscopy for meniscal repair. Reports overall satisfaction with surgical outcome, minimal daily pain; intermittent stiffness and mild discomfort noted mainly after extended periods of sitting or physical activity. Pt keen on resuming full recreational activity (running, yoga). Currently performing routine strengthening and stretching at home, compliant with recommendations thus far.

O:
Vitals:

BP: 116/72 mmHg
HR: 68 bpm
Left knee assessment:

Surgical scars fully healed, no swelling, warmth or erythema.
Knee ROM improved, 0Â° to 130Â°, minor end-range stiffness in flexion.
Quadriceps & hamstring strength improved, 4+/5
Functional assessment: mild difficulty/pain w/ deep squatting; normal gait and balance, no instability.
A:

S/P left knee arthroscopy, excellent recovery, minimal residual stiffness and mild strength deficits
Pt motivated, good candidate for return to previous activities after specific strengthening and mobility protocols.
P:

Initiate formal PT program:
Strengthening (quad/hamstring/gluteal activation & stability exercises)
Stretching/mobility & proprioception activities
Incremental running protocol as tolerated by progress over next 4-6 weeks.
PT sessions: 2x weekly for 6 weeks.
Home exercises provided today, pt educated and demonstrated good understanding.
RTC as scheduled for reassessment at end of PT regimen or sooner if issues arise.
No Rx prescribed today.

Signed:
Alex Carter, PT, DPT
Physical Therapist'),
(
    'SOAP Note - Encounter Date: 2024-03-15 (Follow-Up Visit)',
    'Patient: patient--001
S: Pt returns for follow-up on cholesterol, as planned in prior physical. Labs drawn on previous encounter indicating elevated LDL (165 mg/dL), mildly reduced HDL (38 mg/dL), triglycerides at upper normal limits (145 mg/dL). Pt admits difficulty adhering strictly to suggested dietary changes, but did slightly increase physical activity. Denies chest discomfort, palpitations, SOB, orthopnea, or PND.

O:
Vitals today:

BP: 134/84 mmHg
HR: 78 bpm
Weight stable at 192 lbs
Physical Exam unchanged from last assessment, no new findings.

Review of labs (drawn on 2023-10-26):

LDL cholesterol elevated at 165 mg/dL (desirable <100 mg/dL)
HDL low at 38 mg/dL (desired >40 mg/dL)
Triglycerides borderline at 145 mg/dL (normal <150 mg/dL)
No indications of DM, liver or kidney dysfunction observed on CMP results.

A:

Hyperlipidemia
Overweight status, decreased HDL
Stable vitals, no acute distress or cardiovascular symptoms
P:

Initiate atorvastatin 20 mg PO daily qHS; discussed risks/benefits with pt
Pt advised again regarding diet and lifestyle modifications
Recommend continued aerobic exercise (at least 4 sessions/week, moderate intensity, 30-40 mins per session)
Repeat lipid panel, LFTs after 3 months of statin therapy initiation
Return for follow-up in 3 months or earlier if any adverse reaction occurs.
Prescription Note:

Atorvastatin 20mg tab Disp: #90 (ninety) tabs Sig: 1 tablet PO daily at bedtime Refills: 3
Signed:
Dr. Mark Reynolds, MD
Internal Medicine'
);