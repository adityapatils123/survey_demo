# Copyright 2025 Google LLC
#
# Survey Data and Logic for Otezla Chart Audit Survey

import re
import ast

# Full Survey Data Configuration
SURVEY_DATA = {
  "S1": {
    "question": "Do you or any member of your immediate family have any paid affiliation with the following? Select all that apply.",
    "type": "multiple_choice",
    "options": [
      "Medical Equipment Manufacturer",
      "Market Research, Advertising or Media",
      "Government Drug Approval Organization",
      "Drug Reimbursement Organization",
      "Kaiser, Kaiser Permanente, the Permanente, or the Permanente Medical Group",
      "Pharmaceutical or Biotechnology manufacturer, distributor, retailer, wholesaler, or marketer of pharmaceutical products",
      "None of the above"
    ],
    "next_step": "{ 'TERMINATE' if any(x in str(Output.get('S1','')) for x in ['Medical Equipment Manufacturer','Market Research, Advertising or Media','Government Drug Approval Organization','Drug Reimbursement Organization','Kaiser, Kaiser Permanente, the Permanente, or the Permanente Medical Group']) else 'S2' if 'Pharmaceutical or Biotechnology manufacturer, distributor, retailer, wholesaler, or marketer of pharmaceutical products' in str(Output.get('S1','')) else 'S3' }"
  },
  "S2": {
    "question": "Which of the following best describes your association with the Pharmaceutical Company or Biotechnology manufacturer you are associated with? Select all that apply.",
    "type": "multiple_choice",
    "show_if": "'Pharmaceutical or Biotechnology manufacturer, distributor, retailer, wholesaler, or marketer of pharmaceutical products' in str(Output.get('S1',''))",
    "options": [
      "Paid consultant",
      "Advisory board member",
      "Clinical trial investigator",
      "Other (Please specify)",
      "None of the above"
    ],
    "next_step": "{ 'TERMINATE' if any(x in str(Output.get('S2','')) for x in ['Paid consultant','Clinical trial investigator','Other (Please specify)']) else 'S3' }"
  },
  "S3": {
    "question": "In which states are you currently practicing? Select all that apply.",
    "type": "multiple_choice",
    "options": [
      "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","D.C. - District of Columbia","Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"
    ],
    "next_step": "{ 'TERMINATE' if 'Vermont' in str(Output.get('S3','')) else 'S5' }"
  },
  "S5": {
    "question": "What is your primary medical specialty?",
    "type": "choice",
    "options": [
      "General / Family / Primary care",
      "Dermatology",
      "Internal medicine",
      "Nurse Practitioner (NP)",
      "Physician’s Assistant (PA)",
      "Other (Please specify)"
    ],
    "next_step": "{ 'TERMINATE' if Output.get('S5','') in ['General / Family / Primary care','Internal medicine','Other (Please specify)'] else 'S6' if Output.get('S5','') == 'Dermatology' else 'S8' }"
  },
  "S6": {
    "question": "Are you currently board certified and / or board eligible in your area of specialty?",
    "type": "choice",
    "show_if": "Output.get('S5','') == 'Dermatology'",
    "options": [
      "Board certified",
      "Board eligible",
      "Neither"
    ],
    "next_step": "{ 'TERMINATE' if Output.get('S6','') == 'Neither' else 'S7' }"
  },
  "S7": {
    "question": "For how many years have you practiced in this specialty post-residency? If less than a year, please enter 1.",
    "type": "number",
    "min": 2,
    "max": 35,
    "show_if": "Output.get('S5','') == 'Dermatology'",
    "next_step_in_range": "S10",
    "next_step_out_range": "TERMINATE"
  },
  "S8": {
    "question": "Which of the following best describes the specialty of the practice you primarily work at?",
    "type": "choice",
    "show_if": "Output.get('S5','') in ['Nurse Practitioner (NP)','Physician’s Assistant (PA)']",
    "options": [
      "Dermatology",
      "Primary Care",
      "Other (Please specify)"
    ],
    "next_step": "{ 'TERMINATE' if Output.get('S8','') in ['Primary Care','Other (Please specify)'] else 'S9' }"
  },
  "S9": {
    "question": "For how many years have you been practicing dermatology? If less than a year, please enter 1.",
    "type": "number",
    "min": 2,
    "max": 35,
    "show_if": "Output.get('S5','') in ['Nurse Practitioner (NP)','Physician’s Assistant (PA)'] and Output.get('S8','') == 'Dermatology'",
    "next_step_in_range": "S10",
    "next_step_out_range": "TERMINATE"
  },
  "S10": {
    "question": "What percent of your time do you spend in clinical practice seeing patients?",
    "type": "number",
    "min": 70,
    "max": 100,
    "next_step_in_range": "S11",
    "next_step_out_range": "TERMINATE"
  },
  "S11": {
    "question": "Which of the following describes the setting in which you primarily practice?",
    "type": "choice",
    "options": [
      "Private Practice, with or without a community hospital affiliation",
      "Private Practice, with Academic / teaching hospital affiliation",
      "Academic hospital / research center",
      "Community hospital",
      "Government funded / VA hospital",
      "Other (Please Specify)"
    ],
    "next_step": "{ 'TERMINATE' if Output.get('S11','') in ['Government funded / VA hospital','Other (Please Specify)'] else 'S12_1' }"
  },
  "S12_1": {
    "question": "How many adult (18+) plaque psoriasis patients with Mild disease do you currently manage in a typical 3-month period?",
    "type": "number",
    "min": 0,
    "next_step_in_range": "S12_2"
  },
  "S12_2": {
    "question": "How many adult (18+) plaque psoriasis patients with Moderate disease do you currently manage in a typical 3-month period?",
    "type": "number",
    "min": 0,
    "next_step_in_range": "S12_3"
  },
  "S12_3": {
    "question": "How many adult (18+) plaque psoriasis patients with Severe disease do you currently manage in a typical 3-month period?",
    "type": "number",
    "min": 0,
    "next_step": "{ 'TERMINATE' if ( (Output.get('S5','') == 'Dermatology' and (int(Output.get('S12_1',0)) + int(Output.get('S12_2',0)) + int(Output.get('S12_3',0))) < 70) or (Output.get('S5','') in ['Nurse Practitioner (NP)','Physician’s Assistant (PA)'] and (int(Output.get('S12_1',0)) + int(Output.get('S12_2',0)) + int(Output.get('S12_3',0))) < 50) ) else 'S13_1' }"
  },
  "S13_1": {
    "question": "Mild patients initiated on a new line of treatment in July and August 2025:",
    "type": "number",
    "min": 0,
    "max": "Output['S12_1']",
    "show_if": "int(Output.get('S12_1',0)) > 0",
    "next_step_in_range": "S13_2"
  },
  "S13_2": {
    "question": "Moderate patients initiated on a new line of treatment in July and August 2025:",
    "type": "number",
    "min": 0,
    "max": "Output['S12_2']",
    "show_if": "int(Output.get('S12_2',0)) > 0",
    "next_step_in_range": "S13_3"
  },
  "S13_3": {
    "question": "Severe patients initiated on a new line of treatment in July and August 2025:",
    "type": "number",
    "min": 0,
    "max": "Output['S12_3']",
    "show_if": "int(Output.get('S12_3',0)) > 0",
    "next_step": "{ 'TERMINATE' if ( (int(Output.get('S13_1',0)) + int(Output.get('S13_2',0)) + int(Output.get('S13_3',0)) < 4 and Output.get('S5','') == 'Dermatology') or (int(Output.get('S13_1',0)) + int(Output.get('S13_2',0)) + int(Output.get('S13_3',0)) < 3 and Output.get('S5','') in ['Nurse Practitioner (NP)','Physician’s Assistant (PA)']) ) else 'S14' }"
  },
  "S14": {
    "question": "Which of the following most accurately describes you?",
    "type": "choice",
    "options": [
      "Female",
      "Male",
      "Non-binary",
      "Transgender",
      "Intersex",
      "Other (Please Specify)",
      "Prefer not to say"
    ],
    "next_step": { "default": "S16" }
  },
  "S16": {
    "question": "Consent and Release Form: Market Research Interview/Survey. By selecting an option below, you certify that you are eighteen (18) years old or older, have read and understand the information above, and agree or do not agree to participate.",
    "type": "choice",
    "options": [
      "I consent",
      "I do not consent"
    ],
    "next_step": "{ 'TERMINATE' if Output.get('S16','') == 'I do not consent' else 'END' }"
  },
  "Show_1": {
    "question": "To proceed, you will need at least 4 patient charts (up to 11) that meet the following conditions. Please select your qualified patient charts in July and August and proceed.",
    "type": "show",
    "show_if": "Output.get('S5','') == 'Dermatology'",
    "next_step": "Show_3"
  },
  "Show_2": {
    "question": "To proceed, you will need at least 3 patient charts (up to 9) that meet the following conditions. Please select your qualified patient charts in July and August and proceed.",
    "type": "show",
    "show_if": "Output.get('S5','') in ['Nurse Practitioner (NP)','Physician’s Assistant (PA)']",
    "next_step": "Show_3"
  },
  "Show_3": {
    "question": "In order to capture accurate data, please make sure to select charts for entry that approximate your typical prescribing allocation. For example, if 25% of your plaque psoriasis patients were initiated on Treatment X, we ask that 25% of the charts you enter are for Treatment X.",
    "type": "show",
    "next_step": "A1_1"
  },
  "A1_1": {
    "question": "Please confirm: This patient has mild OR moderate plaque psoriasis with BSA between 2-10%.",
    "type": "choice",
    "options": ["Yes","No"],
    "next_step": "A1_2"
  },
  "A1_2": {
    "question": "Please confirm: This patient has severe plaque psoriasis with BSA above 10%.",
    "type": "choice",
    "options": ["Yes","No"],
    "next_step": "A1_3"
  },
  "A1_3": {
    "question": "Please confirm: This patient is at least 18 years of age.",
    "type": "choice",
    "options": ["Yes","No"],
    "next_step": "A1_4"
  },
  "A1_4": {
    "question": "Please confirm: This patient started on their current plaque psoriasis treatment in July 2025.",
    "type": "choice",
    "options": ["Yes","No"],
    "next_step": "A1_5"
  },
  "A1_5": {
    "question": "Please confirm: This patient started on their current plaque psoriasis treatment in August 2025.",
    "type": "choice",
    "options": ["Yes","No"],
    "next_step": "{ 'Show_4' if (Output.get('A1_1','') == 'No' and Output.get('A1_2','') == 'No') else ('Show_5' if Output.get('A1_3','') == 'No' else ('Show_6' if (Output.get('A1_1','') == 'Yes' and Output.get('A1_2','') == 'Yes') else ('Show_7' if (Output.get('A1_4','') == 'Yes' and Output.get('A1_5','') == 'Yes') else 'A3'))) }"
  },
  "Show_4": {
    "question": "Please select a patient chart that meets the required conditions.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "Show_5": {
    "question": "Please select a patient chart that meets the required conditions.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "Show_6": {
    "question": "Previously, you indicated that this patient has both Mild/Moderate and Severe plaque psoriasis. Please go back and change your answer.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "Show_7": {
    "question": "Previously, you indicated that this patient started treatment in both July and August 2025. Please go back and change your answer.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "A3": {
    "question": "At the time of the treatment initiation in {'July' if Output.get('A1_4','') == 'Yes' else 'August' if Output.get('A1_5','') == 'Yes' else ''} 2025, did you consider this patient’s plaque psoriasis …?",
    "type": "choice",
    "options": ["Mild","Moderate","Severe"],
    "next_step": "{ 'Show_8' if (Output.get('A1_1','') == 'Yes' and Output.get('A3','') == 'Severe') else ('Show_9' if (Output.get('A1_2','') == 'Yes' and Output.get('A3','') in ['Mild','Moderate']) else 'A2') }"
  },
  "Show_8": {
    "question": "Previously, you indicated that this patient has Mild or Moderate plaque psoriasis. Please go back and change your answer.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "Show_9": {
    "question": "Previously, you indicated that this patient has Severe plaque psoriasis. Please go back and change your answer.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "A2": {
    "question": "At the time of the treatment initiation in {'July' if Output.get('A1_4','') == 'Yes' else 'August' if Output.get('A1_5','') == 'Yes' else ''} 2025, what percentage of the patient’s body surface area (BSA) was affected by plaque psoriasis?",
    "type": "number",
    "min": 0,
    "max": 100,
    "next_step": "{ 'Show_10' if (int(Output.get('A2',0)) < 2) else ('Show_11' if (Output.get('A1_1','') == 'Yes' and int(Output.get('A2',0)) > 10) else ('Show_12' if (Output.get('A1_2','') == 'Yes' and int(Output.get('A2',0)) <= 10) else 'A4BN')) }"
  },
  "Show_10": {
    "question": "Please select a patient chart with body surface area affected by plaque psoriasis more than 2%.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "Show_11": {
    "question": "Previously, you indicated that this patient has Mild or Moderate plaque psoriasis with BSA between 2-10%. Please go back and change your answer.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "Show_12": {
    "question": "Previously, you indicated that this patient has Severe plaque psoriasis with BSA above 10%. Please go back and change your answer.",
    "type": "show",
    "next_step": { "default": "A1_1" }
  },
  "A4BN": {
    "question": "Had this patient ever been on a biologic (Anti-TNF, IL-17, IL-23, etc.) or Otezla or Sotyktu prior to {'July' if Output.get('A1_4','') == 'Yes' else 'August' if Output.get('A1_5','') == 'Yes' else ''} 2025?",
    "type": "choice",
    "options": ["Yes","No"],
    "next_step": { "default": "A4" }
  },
  "A4": {
    "question": "In what year was this patient born? (YYYY).",
    "type": "number",
    "min": 1900,
    "max": 2007,
    "next_step_in_range": "A5",
    "next_step_out_range": "A4"
  },
  "A5": {
    "question": "What is this patient’s gender?",
    "type": "choice",
    "options": ["Female","Male","Non-binary","Transgender","Intersex","Other (Please Specify)"],
    "next_step": { "default": "A6" }
  },
  "A6": {
    "question": "What is this person’s race/ethnicity? Select all that apply.",
    "type": "multiple_choice",
    "options": [
      "Caucasian/White",
      "African-American",
      "Asian or Pacific Islander",
      "Hispanic or Latino",
      "Native American or Alaskan Native",
      "Two or more races / ethnicities",
      "Other (Please Specify)"
    ],
    "next_step": { "default": "A7" }
  },
  "A7": {
    "question": "What is this person’s height and weight?",
    "type": "composite_number",
    "sub_fields": [
      { "id": "ft", "label": "Height (ft)", "min": 2, "max": 8 },
      { "id": "in", "label": "Height (in)", "min": 0, "max": 11 },
      { "id": "lbs", "label": "Weight (lbs)", "min": 20, "max": 500 }
    ],
    "options": ["Don't know"],
    "next_step": { "default": "A9" }
  },
  "A9": {
    "question": "What is the patient’s primary type of health insurance?",
    "type": "choice",
    "options": [
      "Private PPO/HMO/Indemnity",
      "Medicare plus supplemental",
      "Medicare only",
      "Medicaid",
      "Other insurance (Please Specify)",
      "No insurance/Cash paying",
      "Don’t know"
    ],
    "next_step": { "default": "B1a" }
  },
  "B1a": {
    "question": "At what age was the patient first diagnosed with plaque psoriasis? (years old)",
    "type": "number_or_unknown",
    "options": ["Don't know"],
    "min": 1,
    "max": 99,
    "next_step_in_range": "B2",
    "next_step": { "default": "B1b" }
  },
  "B1b": {
    "question": "What year was the patient first diagnosed with plaque psoriasis?",
    "type": "number_or_unknown",
    "options": ["Don't know"],
    "min": 1900,
    "max": 2024,
    "next_step_in_range": "B2",
    "next_step": { "default": "B2" }
  },
  "B2": {
    "question": "Does this patient have any of the following comorbidities? Select all that apply.",
    "type": "multiple_choice",
    "options": [
      "Depression",
      "Diabetes",
      "Cardiovascular disease",
      "High blood pressure",
      "High cholesterol",
      "Inflammatory bowel disease (including Crohn’s disease, ulcerative colitis, etc.)",
      "Liver disease/liver abnormalities",
      "Obesity",
      "Rheumatoid arthritis",
      "Skin cancer",
      "Behçet’s Disease",
      "Pulmonary conditions",
      "Other (Please Specify)",
      "None of the above"
    ],
    "next_step": { "default": "B3" }
  },
  "B3": {
    "question": "Has this patient been diagnosed with Psoriatic Arthritis either by you or another physician?",
    "type": "choice",
    "options": ["Yes","No","Don’t know"],
    "next_step": "{ 'B5' if Output.get('B3','') == 'Yes' else 'B6' }"
  },
  "B5": {
    "question": "Do you treat this patient’s Psoriatic Arthritis?",
    "type": "choice",
    "show_if": "Output.get('B3','') == 'Yes'",
    "options": ["Yes","No, treated by Rheumatologist","No, treated by another HCP"],
    "next_step": { "default": "B6" }
  },
  "B6": {
    "question": "At the time of treatment initiation in {'July' if Output.get('A1_4','') == 'Yes' else 'August' if Output.get('A1_5','') == 'Yes' else ''} 2025, which areas of the patient’s body were affected by plaque psoriasis? Select all that apply.",
    "type": "multiple_choice",
    "options": [
      "Nails","Palms","Soles","Hand","Feet","Face","Scalp","Genitals","Intertriginous areas","Knees","Legs","Elbows","Trunk","Arms/forearms","Back","Neck","Other (Please Specify)"
    ],
    "next_step": { "default": "B7" }
  },
  "B7": {
    "question": "Which of the following plaque psoriasis symptoms was this patient experiencing? Select all that apply.",
    "type": "multiple_choice",
    "options": [
      "Whole body itch","Scalp itch","Scales","Painful skin","Skin Redness","Skin Thickness","Skin Flaking","Burning sensation","Skin Bleeding","Skin Stinging","Skin tightness","Joint pain, stiffness or swelling","Nail changes (e.g., pitting, thickening, yellowing, etc.)","Other (Please Specify)"
    ],
    "next_step": { "default": "B8" }
  },
  "B8": {
    "question": "Please rate the impact of the patient’s plaque psoriasis on their quality of life. Use a 1-7 scale, with 1 = no impairment and 7 = severe impairment.",
    "type": "number",
    "min": 1,
    "max": 7,
    "next_step_in_range": "B10",
    "next_step_out_range": "B8"
  },
  "B10": {
    "question": "Over the last year, how many flares, if any, did this patient experience?",
    "type": "number",
    "min": 0,
    "max": 20,
    "next_step_in_range": "T1",
    "next_step_out_range": "T1"
  },
  "T1": {
    "question": "Please select the patient’s current treatment(s) which were first prescribed in {'July' if Output.get('A1_4','') == 'Yes' else 'August' if Output.get('A1_5','') == 'Yes' else ''} 2025. Select all that apply.",
    "type": "multiple_choice",
    "options": [
      "OTC Topical","Clobetasol","Triamcinolone","Betamethasone","Halobetasol","Calcipotriene","Taclonex","Fluocinonide","Enstilar","Duobrii","Eucrisa","Topicort","VTAMA® (tapinarof)","ZORYVE (roflumilast)","Other Topical (Please specify)","Otezla®","Methotrexate","Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)","Sotyktu","Cosentyx®","Taltz®","Stelara®","Tremfya®","Skyrizi®","Enbrel®","Humira®","Bimzelx® (bimekizumab)","Other Biologic (Please specify)"
    ],
    "next_step": "T1b_1"
  },
  "T1b_1": { "question": "Date prescribed for OTC Topical (YYYY-MM-DD).", "type": "text", "show_if": "'OTC Topical' in str(Output.get('T1',''))", "next_step": "T1b_2" },
  "T1b_2": { "question": "Date prescribed for Clobetasol (YYYY-MM-DD).", "type": "text", "show_if": "'Clobetasol' in str(Output.get('T1',''))", "next_step": "T1b_3" },
  "T1b_3": { "question": "Date prescribed for Triamcinolone (YYYY-MM-DD).", "type": "text", "show_if": "'Triamcinolone' in str(Output.get('T1',''))", "next_step": "T1b_4" },
  "T1b_4": { "question": "Date prescribed for Betamethasone (YYYY-MM-DD).", "type": "text", "show_if": "'Betamethasone' in str(Output.get('T1',''))", "next_step": "T1b_5" },
  "T1b_5": { "question": "Date prescribed for Halobetasol (YYYY-MM-DD).", "type": "text", "show_if": "'Halobetasol' in str(Output.get('T1',''))", "next_step": "T1b_6" },
  "T1b_6": { "question": "Date prescribed for Calcipotriene (YYYY-MM-DD).", "type": "text", "show_if": "'Calcipotriene' in str(Output.get('T1',''))", "next_step": "T1b_7" },
  "T1b_7": { "question": "Date prescribed for Taclonex (YYYY-MM-DD).", "type": "text", "show_if": "'Taclonex' in str(Output.get('T1',''))", "next_step": "T1b_8" },
  "T1b_8": { "question": "Date prescribed for Fluocinonide (YYYY-MM-DD).", "type": "text", "show_if": "'Fluocinonide' in str(Output.get('T1',''))", "next_step": "T1b_9" },
  "T1b_9": { "question": "Date prescribed for Enstilar (YYYY-MM-DD).", "type": "text", "show_if": "'Enstilar' in str(Output.get('T1',''))", "next_step": "T1b_10" },
  "T1b_10": { "question": "Date prescribed for Duobrii (YYYY-MM-DD).", "type": "text", "show_if": "'Duobrii' in str(Output.get('T1',''))", "next_step": "T1b_11" },
  "T1b_11": { "question": "Date prescribed for Eucrisa (YYYY-MM-DD).", "type": "text", "show_if": "'Eucrisa' in str(Output.get('T1',''))", "next_step": "T1b_12" },
  "T1b_12": { "question": "Date prescribed for Topicort (YYYY-MM-DD).", "type": "text", "show_if": "'Topicort' in str(Output.get('T1',''))", "next_step": "T1b_26" },
  "T1b_26": { "question": "Date prescribed for VTAMA® (tapinarof) (YYYY-MM-DD).", "type": "text", "show_if": "'VTAMA® (tapinarof)' in str(Output.get('T1',''))", "next_step": "T1b_27" },
  "T1b_27": { "question": "Date prescribed for ZORYVE (roflumilast) (YYYY-MM-DD).", "type": "text", "show_if": "'ZORYVE (roflumilast)' in str(Output.get('T1',''))", "next_step": "T1b_13" },
  "T1b_13": { "question": "Date prescribed for Other Topical (YYYY-MM-DD).", "type": "text", "show_if": "'Other Topical (Please specify)' in str(Output.get('T1',''))", "next_step": "T1_13_spec" },
  "T1_13_spec": { "question": "Please specify the Other Topical.", "type": "text", "show_if": "'Other Topical (Please specify)' in str(Output.get('T1',''))", "next_step": "T1b_14" },
  "T1b_14": { "question": "Date prescribed for Otezla® (YYYY-MM-DD).", "type": "text", "show_if": "'Otezla®' in str(Output.get('T1',''))", "next_step": "T1b_15" },
  "T1b_15": { "question": "Date prescribed for Methotrexate (YYYY-MM-DD).", "type": "text", "show_if": "'Methotrexate' in str(Output.get('T1',''))", "next_step": "T1b_16" },
  "T1b_16": { "question": "Date prescribed for Other Oral Systemics (YYYY-MM-DD).", "type": "text", "show_if": "'Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)' in str(Output.get('T1',''))", "next_step": "T1_16_spec" },
  "T1_16_spec": { "question": "Please specify the Other Oral Systemic.", "type": "text", "show_if": "'Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)' in str(Output.get('T1',''))", "next_step": "T1b_28" },
  "T1b_28": { "question": "Date prescribed for Sotyktu (YYYY-MM-DD).", "type": "text", "show_if": "'Sotyktu' in str(Output.get('T1',''))", "next_step": "T1b_17" },
  "T1b_17": { "question": "Date prescribed for Cosentyx® (YYYY-MM-DD).", "type": "text", "show_if": "'Cosentyx®' in str(Output.get('T1',''))", "next_step": "T1b_18" },
  "T1b_18": { "question": "Date prescribed for Taltz® (YYYY-MM-DD).", "type": "text", "show_if": "'Taltz®' in str(Output.get('T1',''))", "next_step": "T1b_19" },
  "T1b_19": { "question": "Date prescribed for Stelara® (YYYY-MM-DD).", "type": "text", "show_if": "'Stelara®' in str(Output.get('T1',''))", "next_step": "T1b_20" },
  "T1b_20": { "question": "Date prescribed for Tremfya® (YYYY-MM-DD).", "type": "text", "show_if": "'Tremfya®' in str(Output.get('T1',''))", "next_step": "T1b_21" },
  "T1b_21": { "question": "Date prescribed for Skyrizi® (YYYY-MM-DD).", "type": "text", "show_if": "'Skyrizi®' in str(Output.get('T1',''))", "next_step": "T1b_22" },
  "T1b_22": { "question": "Date prescribed for Enbrel® (YYYY-MM-DD).", "type": "text", "show_if": "'Enbrel®' in str(Output.get('T1',''))", "next_step": "T1b_23" },
  "T1b_23": { "question": "Date prescribed for Humira® (YYYY-MM-DD).", "type": "text", "show_if": "'Humira®' in str(Output.get('T1',''))", "next_step": "T1b_29" },
  "T1b_29": { "question": "Date prescribed for Bimzelx® (bimekizumab) (YYYY-MM-DD).", "type": "text", "show_if": "'Bimzelx® (bimekizumab)' in str(Output.get('T1',''))", "next_step": "T1b_24" },
  "T1b_24": { "question": "Date prescribed for Other Biologic (YYYY-MM-DD).", "type": "text", "show_if": "'Other Biologic (Please specify)' in str(Output.get('T1',''))", "next_step": "T1_24_spec" },
  "T1_24_spec": { "question": "Please specify the Other Biologic.", "type": "text", "show_if": "'Other Biologic (Please specify)' in str(Output.get('T1',''))", "next_step": "{ 'Show_13' if (any(x in str(Output.get('T1','')) for x in ['OTC Topical','Clobetasol','Triamcinolone','Betamethasone','Halobetasol','Calcipotriene','Taclonex','Fluocinonide','Enstilar','Duobrii','Eucrisa','Topicort','VTAMA® (tapinarof)','ZORYVE (roflumilast)','Other Topical (Please specify)']) and int(Output.get('A2',0)) > 10 and not any(x in str(Output.get('T1','')) for x in ['Otezla®','Methotrexate','Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)','Sotyktu','Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Bimzelx® (bimekizumab)','Other Biologic (Please specify)'])) else ('Show_14' if (sum(1 for x in ['Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Bimzelx® (bimekizumab)'] if x in str(Output.get('T1',''))) >= 2) else 'T7') }" },
  "Show_13": {
    "question": "You mentioned that this patient has severe plaque psoriasis and was prescribed only topical treatment. Would you please confirm that this is correct?",
    "type": "show",
    "next_step": { "default": "T7" }
  },
  "Show_14": {
    "question": "You mentioned that this patient was placed on the following biologics: {', '.join([x for x in ['Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Bimzelx® (bimekizumab)'] if x in str(Output.get('T1',''))])}. Would you please confirm that this is correct?",
    "type": "show",
    "next_step": { "default": "T7" }
  },
  "T7": {
    "question": "Does the patient struggle with the current treatment?",
    "type": "choice",
    "show_if": "Output.get('A4BN','') == 'No' and not any(x in str(Output.get('T1','')) for x in ['Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Bimzelx® (bimekizumab)','Otezla®','Sotyktu'])",
    "options": ["Yes","No"],
    "next_step": "{ 'T7a' if Output.get('T7','') == 'Yes' else 'T8' }"
  },
  "T7a": {
    "question": "Please explain why the patient is struggling with their current treatment clinically.",
    "type": "text",
    "show_if": "Output.get('T7','') == 'Yes'",
    "next_step": "T7b"
  },
  "T7b": {
    "question": "Please explain why the patient is struggling with their current treatment non-clinically.",
    "type": "text",
    "show_if": "Output.get('T7','') == 'Yes'",
    "next_step": "T8"
  },
  "T8": {
    "question": "How many topicals have you personally prescribed this patient up to and including their current treatment? Please only include treatments you have prescribed, not ones they may have been on previously with another provider.",
    "type": "number",
    "min": 0,
    "show_if": "any(x in str(Output.get('T1','')) for x in ['OTC Topical','Clobetasol','Triamcinolone','Betamethasone','Halobetasol','Calcipotriene','Taclonex','Fluocinonide','Enstilar','Duobrii','Eucrisa','Topicort','VTAMA® (tapinarof)','ZORYVE (roflumilast)','Other Topical (Please specify)']) and not any(x in str(Output.get('T1','')) for x in ['Otezla®','Methotrexate','Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)','Sotyktu','Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Bimzelx® (bimekizumab)','Other Biologic (Please specify)'])",
    "next_step_in_range": "T1z",
    "next_step_out_range": "T1z"
  },
  "T1z": {
    "question": "Which ZORYVE product was prescribed to this patient?",
    "type": "choice",
    "show_if": "'ZORYVE (roflumilast)' in str(Output.get('T1',''))",
    "options": ["Cream","Foam","Both"],
    "next_step": "{ 'T1zf' if Output.get('T1z','') == 'Foam' else 'T2a_1' }"
  },
  "T1zf": {
    "question": "What was ZORYVE prescribed for?",
    "type": "choice",
    "show_if": "Output.get('T1z','') == 'Foam'",
    "options": ["Seborrheic dermatitis","Psoriasis on the body","Psoriasis on the scalp","Psoriasis on both the body and scalp","Other use (please specify)"],
    "next_step": { "default": "T2a_1" }
  },
  "T2a_1": {
    "question": "Please select the primary reason why you selected this therapy for this patient: {Output.get('T1', [])[0] if len(Output.get('T1', []))>=1 else ''}",
    "type": "choice",
    "show_if": "len(Output.get('T1', [])) >= 1",
    "options": [
      "Treatment Cost","Insurance","Patient Preference","Accessibility","Efficacy on addressing symptoms of the joints","Efficacy on skin clearance","Efficacy on DTTA & skin symptoms","Product safety profile","Improvement in QoL & Physical Function","Dosing frequency","Other (Please Specify)"
    ],
    "next_step": "T2a_2"
  },
  "T2a_2": {
    "question": "Please select the primary reason why you selected this therapy for this patient: {Output.get('T1', [])[1] if len(Output.get('T1', []))>=2 else ''}",
    "type": "choice",
    "show_if": "len(Output.get('T1', [])) >= 2",
    "options": [
      "Treatment Cost","Insurance","Patient Preference","Accessibility","Efficacy on addressing symptoms of the joints","Efficacy on skin clearance","Efficacy on DTTA & skin symptoms","Product safety profile","Improvement in QoL & Physical Function","Dosing frequency","Other (Please Specify)"
    ],
    "next_step": "T2a_3"
  },
  "T2a_3": {
    "question": "Please select the primary reason why you selected this therapy for this patient: {Output.get('T1', [])[2] if len(Output.get('T1', []))>=3 else ''}",
    "type": "choice",
    "show_if": "len(Output.get('T1', [])) >= 3",
    "options": [
      "Treatment Cost","Insurance","Patient Preference","Accessibility","Efficacy on addressing symptoms of the joints","Efficacy on skin clearance","Efficacy on DTTA & skin symptoms","Product safety profile","Improvement in QoL & Physical Function","Dosing frequency","Other (Please Specify)"
    ],
    "next_step": "T2b_1"
  },
  "T2b_1": {
    "question": "Select any additional reasons for choosing: {Output.get('T1', [])[0] if len(Output.get('T1', []))>=1 else ''}. Select all that apply.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 1",
    "options": [
      "Treatment Cost","Insurance","Patient Preference","Accessibility","Efficacy on addressing symptoms of the joints","Efficacy on skin clearance","Efficacy on DTTA & skin symptoms","Product safety profile","Improvement in QoL & Physical Function","Dosing frequency","Other (Please Specify)","I don’t have additional reasons"
    ],
    "next_step": "T2b_2"
  },
  "T2b_2": {
    "question": "Select any additional reasons for choosing: {Output.get('T1', [])[1] if len(Output.get('T1', []))>=2 else ''}. Select all that apply.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 2",
    "options": [
      "Treatment Cost","Insurance","Patient Preference","Accessibility","Efficacy on addressing symptoms of the joints","Efficacy on skin clearance","Efficacy on DTTA & skin symptoms","Product safety profile","Improvement in QoL & Physical Function","Dosing frequency","Other (Please Specify)","I don’t have additional reasons"
    ],
    "next_step": "T2b_3"
  },
  "T2b_3": {
    "question": "Select any additional reasons for choosing: {Output.get('T1', [])[2] if len(Output.get('T1', []))>=3 else ''}. Select all that apply.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 3",
    "options": [
      "Treatment Cost","Insurance","Patient Preference","Accessibility","Efficacy on addressing symptoms of the joints","Efficacy on skin clearance","Efficacy on DTTA & skin symptoms","Product safety profile","Improvement in QoL & Physical Function","Dosing frequency","Other (Please Specify)","I don’t have additional reasons"
    ],
    "next_step": "{ 'T2c' if any(x in str(Output.get('T1','')) for x in ['VTAMA® (tapinarof)','ZORYVE (roflumilast)']) else 'T3_A' }"
  },
  "T2c": {
    "question": "We are trying to understand more about your prescription approach towards {', '.join([x for x in Output.get('T1', []) if x in ['VTAMA® (tapinarof)','ZORYVE (roflumilast)']])}. Why did you select this therapy for this patient?",
    "type": "choice",
    "options": [
      "I want to keep the patient on a topical but need better efficacy than topical steroids can provide",
      "I want to keep the patient on a topical and this is safer than topical steroid",
      "I want to delay the potential use of a systemic treatment on this patient",
      "I think I may avoid systemics altogether with this novel topical on this patient",
      "I want to try it since it is newer available treatment class",
      "I had an available sample to give this patient",
      "Other (please specify)"
    ],
    "show_if": "any(x in str(Output.get('T1','')) for x in ['VTAMA® (tapinarof)','ZORYVE (roflumilast)'])",
    "next_step": { "default": "T3_A" }
  },
  "T3_A": {
    "question": "If this patient’s current therapy(ies) had not been available, which treatments would you have placed this patient on? Rank up to 3 choices. Column A for {Output.get('T1', [])[0] if len(Output.get('T1', []))>=1 else ''}.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 1",
    "options": [
      "OTC Topical","Clobetasol","Triamcinolone","Betamethasone","Halobetasol","Calcipotriene","Taclonex","Fluocinonide","Enstilar","Duobrii","Eucrisa","Topicort","VTAMA® (tapinarof)","ZORYVE (roflumilast)","Other Topical (Please specify)","Otezla®","Methotrexate","Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)","Sotyktu","Cosentyx®","Taltz®","Stelara®","Tremfya®","Skyrizi®","Enbrel®","Humira®","Bimzelx® (bimekizumab)","Other Biologic (Please specify)"
    ],
    "next_step": "T3_B"
  },
  "T3_B": {
    "question": "Alternative treatments for Column B {Output.get('T1', [])[1] if len(Output.get('T1', []))>=2 else ''}. Rank up to 3 choices.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 2",
    "options": [
      "OTC Topical","Clobetasol","Triamcinolone","Betamethasone","Halobetasol","Calcipotriene","Taclonex","Fluocinonide","Enstilar","Duobrii","Eucrisa","Topicort","VTAMA® (tapinarof)","ZORYVE (roflumilast)","Other Topical (Please specify)","Otezla®","Methotrexate","Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)","Sotyktu","Cosentyx®","Taltz®","Stelara®","Tremfya®","Skyrizi®","Enbrel®","Humira®","Bimzelx® (bimekizumab)","Other Biologic (Please specify)"
    ],
    "next_step": "T3_C"
  },
  "T3_C": {
    "question": "Alternative treatments for Column C {Output.get('T1', [])[2] if len(Output.get('T1', []))>=3 else ''}. Rank up to 3 choices.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 3",
    "options": [
      "OTC Topical","Clobetasol","Triamcinolone","Betamethasone","Halobetasol","Calcipotriene","Taclonex","Fluocinonide","Enstilar","Duobrii","Eucrisa","Topicort","VTAMA® (tapinarof)","ZORYVE (roflumilast)","Other Topical (Please specify)","Otezla®","Methotrexate","Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)","Sotyktu","Cosentyx®","Taltz®","Stelara®","Tremfya®","Skyrizi®","Enbrel®","Humira®","Bimzelx® (bimekizumab)","Other Biologic (Please specify)"
    ],
    "next_step": "T4_A"
  },
  "T4_A": {
    "question": "Why did you ultimately choose {Output.get('T1', [])[0] if len(Output.get('T1', []))>=1 else ''} over the first alternative treatment option selected in Column A? Select up to 2 reasons.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 1 and len(Output.get('T3_A', [])) >= 1",
    "options": [
      "Patient Influence","MD Habit","Clinical Efficacy","Safety & Tolerability","Insurance","Decreased dosing frequency","Other (Please specify)"
    ],
    "next_step": "T4_B"
  },
  "T4_B": {
    "question": "Why did you ultimately choose {Output.get('T1', [])[1] if len(Output.get('T1', []))>=2 else ''} over the first alternative treatment option selected in Column B? Select up to 2 reasons.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 2 and len(Output.get('T3_B', [])) >= 1",
    "options": [
      "Patient Influence","MD Habit","Clinical Efficacy","Safety & Tolerability","Insurance","Decreased dosing frequency","Other (Please specify)"
    ],
    "next_step": "T4_C"
  },
  "T4_C": {
    "question": "Why did you ultimately choose {Output.get('T1', [])[2] if len(Output.get('T1', []))>=3 else ''} over the first alternative treatment option selected in Column C? Select up to 2 reasons.",
    "type": "multiple_choice",
    "show_if": "len(Output.get('T1', [])) >= 3 and len(Output.get('T3_C', [])) >= 1",
    "options": [
      "Patient Influence","MD Habit","Clinical Efficacy","Safety & Tolerability","Insurance","Decreased dosing frequency","Other (Please specify)"
    ],
    "next_step": "T9"
  },
  "T9": {
    "question": "Why was systemic treatment not considered for this patient? Select all that apply.",
    "type": "multiple_choice",
    "show_if": "any(x in str(Output.get('T1','')) for x in ['OTC Topical','Clobetasol','Triamcinolone','Betamethasone','Halobetasol','Calcipotriene','Taclonex','Fluocinonide','Enstilar','Duobrii','Eucrisa','Topicort','VTAMA® (tapinarof)','ZORYVE (roflumilast)','Other Topical (Please specify)']) and not any(x in str(Output.get('T1','')) for x in ['Otezla®','Methotrexate','Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)','Sotyktu','Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Bimzelx® (bimekizumab)','Other Biologic (Please specify)'])",
    "options": [
      "Affordability / out-of-pocket costs",
      "Insurance coverage",
      "Patient has more concerning comorbidities",
      "Concerns about patient compliance",
      "Patient refusal",
      "Patient history with potential side effects",
      "Patient preference for non-systemic treatment",
      "Don’t expect patient’s psoriasis to progress / worsen",
      "Patient is contraindicated",
      "Patient is needle averse",
      "Don’t want to have to conduct initial / ongoing labs",
      "Current medication was effective enough",
      "Other (Please specify)"
    ],
    "next_step": "{ 'T9A' if 'Patient refusal' in str(Output.get('T9','')) else 'A3BSA' }"
  },
  "T9A": {
    "question": "Why did this patient refuse your recommendation for systemic treatment? Select all that apply.",
    "type": "multiple_choice",
    "show_if": "'Patient refusal' in str(Output.get('T9',''))",
    "options": [
      "Concern about affordability / out of pocket costs",
      "Concern it wouldn’t be covered by insurance",
      "Patient decided current medication was effective enough",
      "Patient refusal due to more concerning comorbidities",
      "Patient preferred less aggressive therapy",
      "Patient concern with potential side effects",
      "Patient preference for specific ROA",
      "Patient did not understand the long-term, systemic implications of having uncontrolled PsO",
      "Patient is needle averse",
      "Patient did not want to have to do initial / on-going labs",
      "Inability to start on treatment today / immediately",
      "Other (Please specify)"
    ],
    "next_step": { "default": "A3BSA" }
  },
  "A3BSA": {
    "question": "How likely is this patient to go on systemic treatment for their plaque psoriasis within the next year?",
    "type": "choice",
    "show_if": "any(x in str(Output.get('T1','')) for x in ['OTC Topical','Clobetasol','Triamcinolone','Betamethasone','Halobetasol','Calcipotriene','Taclonex','Fluocinonide','Enstilar','Duobrii','Eucrisa','Topicort','VTAMA® (tapinarof)','ZORYVE (roflumilast)','Other Topical (Please specify)']) and not any(x in str(Output.get('T1','')) for x in ['Otezla®','Methotrexate','Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)','Sotyktu','Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Bimzelx® (bimekizumab)','Other Biologic (Please specify)'])",
    "options": [
      "Very unlikely","Unlikely","Somewhat unlikely","Somewhat likely","Likely","Very likely"
    ],
    "next_step": "{ 'A5BSA' if Output.get('A3BSA','') in ['Somewhat likely','Likely','Very likely'] else 'A10' }"
  },
  "A5BSA": {
    "question": "You mentioned this patient is at least somewhat likely to go onto systemic treatment. What are the reasons why this patient is expected to go on a systemic treatment in the future? Select up to 3 reasons.",
    "type": "multiple_choice",
    "show_if": "Output.get('A3BSA','') in ['Somewhat likely','Likely','Very likely']",
    "options": [
      "Patient has insufficient skin clearance on topicals alone",
      "Patient has a difficult to treat psoriasis area (e.g., scalp, genital, palms)",
      "Patient symptoms are not controlled (e.g., itch, skin tightness)",
      "Patient is experiencing frequent flares",
      "Patient’s plaque presentation (e.g., thick plaques, thick scales)",
      "I expect the patient’s psoriasis to progress / worsen",
      "Current PsO presentation indicates signs of PsA (e.g., nail PsO)",
      "Patient is growing tired of topicals",
      "Patient’s self-esteem and / or quality of life is becoming impacted",
      "Future insurance changes may approve systemic treatment",
      "Patient has family history of more severe PsO and / or active PsA",
      "Patient has begun asking about systemic treatment",
      "PsO is a chronic disease and may need a systemic in the long-term",
      "Other (Please specify)"
    ],
    "next_step": { "default": "A4BSA" }
  },
  "A4BSA": {
    "question": "In how many months from now would you expect this patient to start systemic treatment?",
    "type": "number_or_unknown",
    "options": ["Don’t know"],
    "min": 0,
    "max": 24,
    "show_if": "Output.get('A3BSA','') in ['Somewhat likely','Likely','Very likely']",
    "next_step_in_range": "A6BSA",
    "next_step": { "default": "A6BSA" }
  },
  "A6BSA": {
    "question": "What systemic treatment are you most likely to start this patient on? Select one.",
    "type": "choice",
    "show_if": "Output.get('A3BSA','') in ['Somewhat likely','Likely','Very likely']",
    "options": [
      "Otezla®","Methotrexate","Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)","Sotyktu","Cosentyx®","Taltz®","Stelara®","Tremfya®","Skyrizi®","Enbrel®","Humira®","Bimzelx® (bimekizumab)","Other Biologic (Please specify)"
    ],
    "next_step": { "default": "A10" }
  },
  "A10": {
    "question": "Did this patient request a specific product by name or description?",
    "type": "choice",
    "options": ["Yes","No"],
    "next_step": "{ 'A10a' if Output.get('A10','') == 'Yes' else 'A8' }"
  },
  "A10a": {
    "question": "Which product did this patient request?",
    "type": "choice",
    "show_if": "Output.get('A10','') == 'Yes'",
    "options": [
      "Otezla®","Skyrizi®","Humira®","VTAMA® (tapinarof)","ZORYVE (roflumilast)","Sotyktu","Taltz®","Stelara®","Tremfya®","Cosentyx®","Bimzelx® (bimekizumab)"
    ],
    "next_step": { "default": "A10B" }
  },
  "A10B": {
    "question": "What was the main reason this patient requested {Output.get('A10a','')}?",
    "type": "text",
    "show_if": "Output.get('A10','') == 'Yes'",
    "next_step": { "default": "A8" }
  },
  "A8": {
    "question": "Rank three most important factors for this patient when considering treatment options for plaque psoriasis.",
    "type": "multiple_choice",
    "options": [
      "Affordability",
      "Route of administration",
      "Dosing frequency",
      "Speed of onset",
      "Tolerability/side effects",
      "Out-of-pocket cost",
      "Ease of patient access",
      "Reduction in the amount of medications/treatments patient has to take overall",
      "Product that patient trusts",
      "Side effects",
      "Long-lasting effect",
      "Doctor recommendation",
      "Doesn’t need monitoring by a doctor",
      "No need for Lab work",
      "Other (please specify)"
    ],
    "next_step": { "default": "A11" }
  },
  "A11": {
    "question": "What is this patient’s attitude towards the route of administration?",
    "type": "choice",
    "options": [
      "Patient prefers oral treatment over self-injection",
      "Patient does not express a specific preference",
      "Patient prefers self-injection over oral treatment"
    ],
    "next_step": { "default": "T6" }
  },
  "T6": {
    "question": "Other than the patient’s current plaque psoriasis treatments {Output.get('T1','')}, what treatments has this patient started in the past 3 years (since {'July' if Output.get('A1_4','') == 'Yes' else 'August' if Output.get('A1_5','') == 'Yes' else ''} 2022)? Select all that apply.",
    "type": "multiple_choice",
    "options": [
      "OTC Topical","Clobetasol","Triamcinolone","Betamethasone","Halobetasol","Calcipotriene","Taclonex","Fluocinonide","Enstilar","Duobrii","Eucrisa","Topicort","VTAMA® (tapinarof)","ZORYVE (roflumilast)","Other Topical (Please specify)","Otezla®","Methotrexate","Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)","Sotyktu","Cosentyx®","Taltz®","Stelara®","Tremfya®","Skyrizi®","Enbrel®","Humira®","Bimzelx® (bimekizumab)","Other Biologic (Please specify)","Phototherapy","None"
    ],
    "next_step": "T6_b_1"
  },
  "T6_b_1": { "question": "Date of first administration for OTC Topical (YYYY-MM-DD).", "type": "text", "show_if": "'OTC Topical' in str(Output.get('T6',''))", "next_step": "T6_c_1" },
  "T6_c_1": { "question": "Date of last administration for OTC Topical (YYYY-MM-DD).", "type": "text", "show_if": "'OTC Topical' in str(Output.get('T6',''))", "next_step": "T6_b_2" },
  "T6_b_2": { "question": "Date of first administration for Clobetasol (YYYY-MM-DD).", "type": "text", "show_if": "'Clobetasol' in str(Output.get('T6',''))", "next_step": "T6_c_2" },
  "T6_c_2": { "question": "Date of last administration for Clobetasol (YYYY-MM-DD).", "type": "text", "show_if": "'Clobetasol' in str(Output.get('T6',''))", "next_step": "T6_b_3" },
  "T6_b_3": { "question": "Date of first administration for Triamcinolone (YYYY-MM-DD).", "type": "text", "show_if": "'Triamcinolone' in str(Output.get('T6',''))", "next_step": "T6_c_3" },
  "T6_c_3": { "question": "Date of last administration for Triamcinolone (YYYY-MM-DD).", "type": "text", "show_if": "'Triamcinolone' in str(Output.get('T6',''))", "next_step": "T6_b_4" },
  "T6_b_4": { "question": "Date of first administration for Betamethasone (YYYY-MM-DD).", "type": "text", "show_if": "'Betamethasone' in str(Output.get('T6',''))", "next_step": "T6_c_4" },
  "T6_c_4": { "question": "Date of last administration for Betamethasone (YYYY-MM-DD).", "type": "text", "show_if": "'Betamethasone' in str(Output.get('T6',''))", "next_step": "T6_b_5" },
  "T6_b_5": { "question": "Date of first administration for Halobetasol (YYYY-MM-DD).", "type": "text", "show_if": "'Halobetasol' in str(Output.get('T6',''))", "next_step": "T6_c_5" },
  "T6_c_5": { "question": "Date of last administration for Halobetasol (YYYY-MM-DD).", "type": "text", "show_if": "'Halobetasol' in str(Output.get('T6',''))", "next_step": "T6_b_6" },
  "T6_b_6": { "question": "Date of first administration for Calcipotriene (YYYY-MM-DD).", "type": "text", "show_if": "'Calcipotriene' in str(Output.get('T6',''))", "next_step": "T6_c_6" },
  "T6_c_6": { "question": "Date of last administration for Calcipotriene (YYYY-MM-DD).", "type": "text", "show_if": "'Calcipotriene' in str(Output.get('T6',''))", "next_step": "T6_b_7" },
  "T6_b_7": { "question": "Date of first administration for Taclonex (YYYY-MM-DD).", "type": "text", "show_if": "'Taclonex' in str(Output.get('T6',''))", "next_step": "T6_c_7" },
  "T6_c_7": { "question": "Date of last administration for Taclonex (YYYY-MM-DD).", "type": "text", "show_if": "'Taclonex' in str(Output.get('T6',''))", "next_step": "T6_b_8" },
  "T6_b_8": { "question": "Date of first administration for Fluocinonide (YYYY-MM-DD).", "type": "text", "show_if": "'Fluocinonide' in str(Output.get('T6',''))", "next_step": "T6_c_8" },
  "T6_c_8": { "question": "Date of last administration for Fluocinonide (YYYY-MM-DD).", "type": "text", "show_if": "'Fluocinonide' in str(Output.get('T6',''))", "next_step": "T6_b_9" },
  "T6_b_9": { "question": "Date of first administration for Enstilar (YYYY-MM-DD).", "type": "text", "show_if": "'Enstilar' in str(Output.get('T6',''))", "next_step": "T6_c_9" },
  "T6_c_9": { "question": "Date of last administration for Enstilar (YYYY-MM-DD).", "type": "text", "show_if": "'Enstilar' in str(Output.get('T6',''))", "next_step": "T6_b_10" },
  "T6_b_10": { "question": "Date of first administration for Duobrii (YYYY-MM-DD).", "type": "text", "show_if": "'Duobrii' in str(Output.get('T6',''))", "next_step": "T6_c_10" },
  "T6_c_10": { "question": "Date of last administration for Duobrii (YYYY-MM-DD).", "type": "text", "show_if": "'Duobrii' in str(Output.get('T6',''))", "next_step": "T6_b_11" },
  "T6_b_11": { "question": "Date of first administration for Eucrisa (YYYY-MM-DD).", "type": "text", "show_if": "'Eucrisa' in str(Output.get('T6',''))", "next_step": "T6_c_11" },
  "T6_c_11": { "question": "Date of last administration for Eucrisa (YYYY-MM-DD).", "type": "text", "show_if": "'Eucrisa' in str(Output.get('T6',''))", "next_step": "T6_b_12" },
  "T6_b_12": { "question": "Date of first administration for Topicort (YYYY-MM-DD).", "type": "text", "show_if": "'Topicort' in str(Output.get('T6',''))", "next_step": "T6_c_12" },
  "T6_c_12": { "question": "Date of last administration for Topicort (YYYY-MM-DD).", "type": "text", "show_if": "'Topicort' in str(Output.get('T6',''))", "next_step": "T6_b_26" },
  "T6_b_26": { "question": "Date of first administration for VTAMA® (tapinarof) (YYYY-MM-DD).", "type": "text", "show_if": "'VTAMA® (tapinarof)' in str(Output.get('T6',''))", "next_step": "T6_c_26" },
  "T6_c_26": { "question": "Date of last administration for VTAMA® (tapinarof) (YYYY-MM-DD).", "type": "text", "show_if": "'VTAMA® (tapinarof)' in str(Output.get('T6',''))", "next_step": "T6_b_27" },
  "T6_b_27": { "question": "Date of first administration for ZORYVE (roflumilast) (YYYY-MM-DD).", "type": "text", "show_if": "'ZORYVE (roflumilast)' in str(Output.get('T6',''))", "next_step": "T6_c_27" },
  "T6_c_27": { "question": "Date of last administration for ZORYVE (roflumilast) (YYYY-MM-DD).", "type": "text", "show_if": "'ZORYVE (roflumilast)' in str(Output.get('T6',''))", "next_step": "T6_b_13" },
  "T6_b_13": { "question": "Date of first administration for Other Topical (YYYY-MM-DD).", "type": "text", "show_if": "'Other Topical (Please specify)' in str(Output.get('T6',''))", "next_step": "T6_c_13" },
  "T6_c_13": { "question": "Date of last administration for Other Topical (YYYY-MM-DD).", "type": "text", "show_if": "'Other Topical (Please specify)' in str(Output.get('T6',''))", "next_step": "T6_b_14" },
  "T6_b_14": { "question": "Date of first administration for Otezla® (YYYY-MM-DD).", "type": "text", "show_if": "'Otezla®' in str(Output.get('T6',''))", "next_step": "T6_c_14" },
  "T6_c_14": { "question": "Date of last administration for Otezla® (YYYY-MM-DD).", "type": "text", "show_if": "'Otezla®' in str(Output.get('T6',''))", "next_step": "T6_b_15" },
  "T6_b_15": { "question": "Date of first administration for Methotrexate (YYYY-MM-DD).", "type": "text", "show_if": "'Methotrexate' in str(Output.get('T6',''))", "next_step": "T6_c_15" },
  "T6_c_15": { "question": "Date of last administration for Methotrexate (YYYY-MM-DD).", "type": "text", "show_if": "'Methotrexate' in str(Output.get('T6',''))", "next_step": "T6_b_16" },
  "T6_b_16": { "question": "Date of first administration for Other Oral Systemics (YYYY-MM-DD).", "type": "text", "show_if": "'Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)' in str(Output.get('T6',''))", "next_step": "T6_c_16" },
  "T6_c_16": { "question": "Date of last administration for Other Oral Systemics (YYYY-MM-DD).", "type": "text", "show_if": "'Other Oral Systemics (e.g. leflunomide, sulfasalazine, etc.)' in str(Output.get('T6',''))", "next_step": "T6_b_28" },
  "T6_b_28": { "question": "Date of first administration for Sotyktu (YYYY-MM-DD).", "type": "text", "show_if": "'Sotyktu' in str(Output.get('T6',''))", "next_step": "T6_c_28" },
  "T6_c_28": { "question": "Date of last administration for Sotyktu (YYYY-MM-DD).", "type": "text", "show_if": "'Sotyktu' in str(Output.get('T6',''))", "next_step": "T6_b_17" },
  "T6_b_17": { "question": "Date of first administration for Cosentyx® (YYYY-MM-DD).", "type": "text", "show_if": "'Cosentyx®' in str(Output.get('T6',''))", "next_step": "T6_c_17" },
  "T6_c_17": { "question": "Date of last administration for Cosentyx® (YYYY-MM-DD).", "type": "text", "show_if": "'Cosentyx®' in str(Output.get('T6',''))", "next_step": "T6_b_18" },
  "T6_b_18": { "question": "Date of first administration for Taltz® (YYYY-MM-DD).", "type": "text", "show_if": "'Taltz®' in str(Output.get('T6',''))", "next_step": "T6_c_18" },
  "T6_c_18": { "question": "Date of last administration for Taltz® (YYYY-MM-DD).", "type": "text", "show_if": "'Taltz®' in str(Output.get('T6',''))", "next_step": "T6_b_19" },
  "T6_b_19": { "question": "Date of first administration for Stelara® (YYYY-MM-DD).", "type": "text", "show_if": "'Stelara®' in str(Output.get('T6',''))", "next_step": "T6_c_19" },
  "T6_c_19": { "question": "Date of last administration for Stelara® (YYYY-MM-DD).", "type": "text", "show_if": "'Stelara®' in str(Output.get('T6',''))", "next_step": "T6_b_20" },
  "T6_b_20": { "question": "Date of first administration for Tremfya® (YYYY-MM-DD).", "type": "text", "show_if": "'Tremfya®' in str(Output.get('T6',''))", "next_step": "T6_c_20" },
  "T6_c_20": { "question": "Date of last administration for Tremfya® (YYYY-MM-DD).", "type": "text", "show_if": "'Tremfya®' in str(Output.get('T6',''))", "next_step": "T6_b_21" },
  "T6_b_21": { "question": "Date of first administration for Skyrizi® (YYYY-MM-DD).", "type": "text", "show_if": "'Skyrizi®' in str(Output.get('T6',''))", "next_step": "T6_c_21" },
  "T6_c_21": { "question": "Date of last administration for Skyrizi® (YYYY-MM-DD).", "type": "text", "show_if": "'Skyrizi®' in str(Output.get('T6',''))", "next_step": "T6_b_22" },
  "T6_b_22": { "question": "Date of first administration for Enbrel® (YYYY-MM-DD).", "type": "text", "show_if": "'Enbrel®' in str(Output.get('T6',''))", "next_step": "T6_c_22" },
  "T6_c_22": { "question": "Date of last administration for Enbrel® (YYYY-MM-DD).", "type": "text", "show_if": "'Enbrel®' in str(Output.get('T6',''))", "next_step": "T6_b_23" },
  "T6_b_23": { "question": "Date of first administration for Humira® (YYYY-MM-DD).", "type": "text", "show_if": "'Humira®' in str(Output.get('T6',''))", "next_step": "T6_c_23" },
  "T6_c_23": { "question": "Date of last administration for Humira® (YYYY-MM-DD).", "type": "text", "show_if": "'Humira®' in str(Output.get('T6',''))", "next_step": "T6_b_29" },
  "T6_b_29": { "question": "Date of first administration for Bimzelx® (bimekizumab) (YYYY-MM-DD).", "type": "text", "show_if": "'Bimzelx® (bimekizumab)' in str(Output.get('T6',''))", "next_step": "T6_c_29" },
  "T6_c_29": { "question": "Date of last administration for Bimzelx® (bimekizumab) (YYYY-MM-DD).", "type": "text", "show_if": "'Bimzelx® (bimekizumab)' in str(Output.get('T6',''))", "next_step": "T6_b_24" },
  "T6_b_24": { "question": "Date of first administration for Other Biologic (YYYY-MM-DD).", "type": "text", "show_if": "'Other Biologic (Please specify)' in str(Output.get('T6',''))", "next_step": "T6_c_24" },
  "T6_c_24": { "question": "Date of last administration for Other Biologic (YYYY-MM-DD).", "type": "text", "show_if": "'Other Biologic (Please specify)' in str(Output.get('T6',''))", "next_step": "T6_b_25" },
  "T6_b_25": { "question": "Date of first administration for Phototherapy (YYYY-MM-DD).", "type": "text", "show_if": "'Phototherapy' in str(Output.get('T6',''))", "next_step": "T6_c_25" },
  "T6_c_25": { "question": "Date of last administration for Phototherapy (YYYY-MM-DD).", "type": "text", "show_if": "'Phototherapy' in str(Output.get('T6',''))", "next_step": "T6_none_check" },
  "T6_none_check": {
    "question": "Confirmation: You said that this patient has had no other treatments in the past 3 years. Please go back and change your answer or confirm this is correct.",
    "type": "show",
    "show_if": "'None' in str(Output.get('T6',''))",
    "next_step": { "default": "T6" }
  },
  "T6none": {
    "question": "Please explain why you did not prescribe any treatment for this patient before prescribing {', '.join([x for x in Output.get('T1', []) if x in ['Otezla®','Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Sotyktu','Bimzelx® (bimekizumab)']])}.",
    "type": "text",
    "show_if": "'None' in str(Output.get('T6','')) and any(x in str(Output.get('T1','')) for x in ['Otezla®','Cosentyx®','Taltz®','Stelara®','Tremfya®','Skyrizi®','Enbrel®','Humira®','Sotyktu','Bimzelx® (bimekizumab)'])",
    "next_step": { "default": "END" }
  }
}

def match_voice_to_option(answer: str, options: list) -> "str | None":
    """
    Matches voice/spoken answer to an exact option for choice questions.
    Returns the matched option string from the list, or None if no match.
    Enables 'dermatology' -> 'Dermatology', 'none of the above' -> 'None of the above', etc.
    """
    if not answer or not options:
        return None
    a = answer.strip().lower()
    if not a:
        return None
    
    # 1) Exact match (case-insensitive)
    for opt in options:
        if a == opt.lower():
            return opt
            
    # 2) User said a substring of the option: "derm" -> "Dermatology"
    # But be careful with "no" vs "none of the above" or "yes" vs "yes, treated"
    for opt in options:
        # Check if the spoken word is a significant part of the option
        if a in opt.lower():
            return opt
            
    # 3) Option is contained in what user said: "I choose Dermatology" -> "Dermatology"
    for opt in options:
        if opt.lower() in a:
            return opt
            
    # 4) Partial word match for multi-word options: "none" / "advisory board" etc.
    a_words = set(a.split())
    for opt in options:
        opt_words = set(opt.lower().split())
        if opt_words and opt_words <= a_words:
            return opt
        if a_words and a_words <= opt_words:
            # Only if the overlap is significant (e.g. > 50% of words)
            common = a_words.intersection(opt_words)
            if len(common) >= len(opt_words) * 0.5:
                return opt
                
    return None

def evaluate_logic(expression, answers):
    """
    Evaluates python logic strings from the JSON config.
    Adapted from Survery_Code.py.
    """
    if not expression or not isinstance(expression, str):
        return expression
    
    # Remove curly braces if present (JSON format often wraps logic in {})
    clean_expr = expression.replace('{', '').replace('}', '').strip()
    
    if not clean_expr:
        return None

    # Context for eval - ensures all Python functions work
    # We use 'Output' to match the JSON variable name
    eval_context = {
        "Output": answers,
        "answers": answers,
        "int": int, "str": str, "any": any, "all": all, "sum": sum, "bool": bool, "len": len,
        "__builtins__": {} # Restrict builtins for safety
    }
    
    try:
        # Using eval with restricted context
        return eval(clean_expr, eval_context)
    except Exception as e:
        # If it's just a plain Step ID string, logic evaluation might fail if it's not valid python code
        # But usually logic strings are Python expressions. 
        # If evaluation fails, it might be a literal string (though usually literals are quoted in python)
        # Check if it matches a known step ID
        if clean_expr in SURVEY_DATA or clean_expr in ["TERMINATE", "END"]:
            return clean_expr
            
        print(f"Logic Error: {e} in expression: {clean_expr}")
        return None

def get_next_step(current_step, answer, answers):
    """
    Determines the next step based on current step, current answer, and all previous answers.
    Fully dynamic based on SURVEY_DATA logic.
    """
    if current_step not in SURVEY_DATA:
        return "END"
        
    config = SURVEY_DATA[current_step]
    q_type = config.get("type")
    logic = config.get("next_step")
    
    # If the answer hasn't been saved to 'answers' yet, we should temporarily add it for logic evaluation
    # (The caller usually saves it, but just in case)
    temp_answers = answers.copy()
    temp_answers[current_step] = answer

    # 1. ALWAYS check if next_step is a Logic Expression first
    if isinstance(logic, str) and ("Output" in logic or "any(" in logic or "if" in logic):
        result = evaluate_logic(logic, temp_answers)
        if result in SURVEY_DATA or result in ["END", "TERMINATE"]:
            return result
        # If logic returned a step ID that exists, return it
        if isinstance(result, str) and (result in SURVEY_DATA or result == "END" or result == "TERMINATE"):
            return result

    # 2. HANDLE NUMERIC TYPES (Ranges)
    if q_type in ["number", "number_or_unknown"]:
        # Check if answer is "Don't know" or similar special option
        if isinstance(answer, str) and not answer.isdigit():
             if isinstance(logic, dict):
                 return logic.get(answer, logic.get("default", "TERMINATE"))
        
        try:
            val = int(answer)
            # Evaluate min/max if they are expressions
            min_val = config.get("min", -999999)
            max_val = config.get("max", 999999)
            
            if isinstance(min_val, str):
                min_val = evaluate_logic(min_val, temp_answers)
            if isinstance(max_val, str):
                max_val = evaluate_logic(max_val, temp_answers)
                
            if int(min_val) <= val <= int(max_val):
                if "next_step_in_range" in config:
                    return config["next_step_in_range"]
            else:
                if "next_step_out_range" in config:
                    return config["next_step_out_range"]
        except:
            pass

    # 3. HANDLE PLAIN STRINGS (Simple jumps)
    if isinstance(logic, str):
        # If it's a simple string like "S2" (and wasn't an expression)
        if logic in SURVEY_DATA or logic in ["END", "TERMINATE"]:
            return logic

    # 4. HANDLE DICTIONARY MAPPING (Standard Choice questions)
    if isinstance(logic, dict):
        if answer in logic:
            return logic[answer]
        return logic.get("default", "TERMINATE")

    # 5. Handling the "Show" type loop logic
    # "show" questions often loop back to a parent or check conditions
    # If standard logic failed, check for implicit flow or default
    
    return "TERMINATE" # Default fallback if nothing matches

def validate_answer(step, answer, answers=None):
    """
    Validates if an answer is acceptable for a given step.
    Supports all question types in SURVEY_DATA.
    """
    if step not in SURVEY_DATA:
        return False, "Invalid step"
    
    question_data = SURVEY_DATA[step]
    q_type = question_data.get("type", "choice")
    options = question_data.get("options", [])
    
    if answers is None:
        answers = {}

    if q_type == "multiple_choice":
        # Expecting a list or a string that might be comma-separated?
        # The agent usually passes a string. If it's multiple, maybe a list?
        # Let's assume the agent passes what the user SAID, or a list if parsed.
        # Ideally, we check if the values are in options.
        if not answer:
            return False, "Please select at least one option."
        
        # If it's a string, it might be a single choice from the multi-choice list
        # or a comma-separated list if the agent handled it.
        # For simplicity in this validation: check if the answer (or parts) are valid options.
        # Note: Voice matching happens before this function usually.
        # If answer is a string and matches one option, it's valid.
        if isinstance(answer, str) and answer in options:
            return True, "Valid"
        
        # If it's a list (from some future UI), check each.
        if isinstance(answer, list):
            if all(a in options for a in answer):
                return True, "Valid"
        
        return True, "Valid" # Relaxed validation for multiple choice voice input

    elif q_type == "choice":
        if answer not in options:
            return False, f"Please select one of the provided options: {', '.join(options[:3])}..."
        return True, "Valid"
    
    elif q_type in ["number", "number_or_unknown"]:
        # Check special options first
        if answer in options:
            return True, "Valid"
            
        try:
            num = int(answer)
            min_val = question_data.get("min", 0)
            max_val = question_data.get("max", 10000)
            
            # Evaluate dynamic min/max
            if isinstance(min_val, str):
                min_val = int(evaluate_logic(min_val, answers) or 0)
            if isinstance(max_val, str):
                max_val = int(evaluate_logic(max_val, answers) or 10000)
                
            if min_val <= num <= max_val:
                return True, "Valid"
            else:
                return False, f"Please enter a number between {min_val} and {max_val}"
        except:
            return False, "Please enter a valid number"
            
    elif q_type == "composite_number":
        # Expecting a dict or a string representation of it? 
        # Or maybe the agent handles one field at a time?
        # The current agent implementation assumes single answer per step.
        # Composite questions might need to be broken down or handled as a complex JSON string.
        # For now, accept if not empty.
        if not answer:
            return False, "Please provide values."
        return True, "Valid"
        
    elif q_type == "text":
        if not answer or not str(answer).strip():
            return False, "Please provide a response."
        return True, "Valid"
        
    elif q_type == "show":
        # 'Show' type usually just needs acknowledgement or "next"
        return True, "Valid"
    
    return True, "Valid"


def get_filtered_survey_data():
    """
    Returns filtered survey data containing only S1-S16 questions for current version.
    Core logic (get_next_step, validate_answer) still uses full SURVEY_DATA.
    This is for UI display only.
    """
    # Define which steps to include (S1-S16 and related Show steps)
    included_steps = set()
    
    # Add S1-S16 (note: S4 doesn't exist, S15 doesn't exist)
    for i in range(1, 17):
        step = f"S{i}"
        if step in SURVEY_DATA:
            included_steps.add(step)
    
    # Also include S12_1, S12_2, S12_3, S13_1, S13_2, S13_3 (sub-steps of S12 and S13)
    sub_steps = ["S12_1", "S12_2", "S12_3", "S13_1", "S13_2", "S13_3"]
    for step in sub_steps:
        if step in SURVEY_DATA:
            included_steps.add(step)
    
    # Include Show steps that are referenced by S16 (Show_1, Show_2, Show_3)
    # show_steps = ["Show_1", "Show_2", "Show_3"]
    # for step in show_steps:
    #     if step in SURVEY_DATA:
    #         included_steps.add(step)
    
    # Always include END and TERMINATE
    included_steps.add("END")
    included_steps.add("TERMINATE")
    
    # Filter SURVEY_DATA to only include these steps
    filtered_data = {step: SURVEY_DATA[step] for step in included_steps if step in SURVEY_DATA}
    
    return filtered_data
