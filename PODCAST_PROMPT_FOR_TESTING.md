# Podcast Script Generation Prompt for IBM Granite 3.3 8B

## System Prompt
```
You are a professional podcast script writer.
```

## User Prompt Template
```
You are a professional podcast script writer. Create an engaging podcast dialogue between a HOST and an EXPERT in English language.

IMPORTANT: Generate the ENTIRE script in English language. All dialogue must be in English.

Topic/Focus: IBM digital transformation

Content from documents:
[Document 1]: IBM's 2024 key performance drivers include our comprehensive, proactive, and AI-enabled services for maintaining and improving availability and value, as well as our rapidly growing ecosystem of cloud, ISVs, hardware, network, and services partners...
[Document 2]: Our full technology stack enables us to meet clients wherever they are in their digital transformations...
[... more RAG documents ...]

Duration: 15 minutes (approximately 2250 words at 150 words/minute)

**Podcast Style:** conversational_interview
**Target Audience:** intermediate
**Language:** en (ALL text must be in this language)

Format your script as a natural conversation with these guidelines:

1. **Structure:**
   - HOST asks insightful questions to guide the conversation
   - EXPERT provides detailed, engaging answers with examples
   - Include natural transitions and follow-up questions
   - Start with a brief introduction from HOST
   - End with a conclusion from HOST

2. **Script Format (IMPORTANT):**
   Use this exact format for each turn:

   HOST: [Question or introduction]
   EXPERT: [Detailed answer with examples]
   HOST: [Follow-up or transition]
   EXPERT: [Further explanation]

3. **Style Guidelines for conversational_interview:**
   - conversational_interview: Use Q&A format with engaging, open-ended questions. HOST should ask follow-ups and show curiosity.
   - narrative: Use storytelling approach with smooth transitions. EXPERT should weave information into a compelling narrative arc.
   - educational: Use structured learning format. Break down concepts clearly with examples. Build from basics to advanced topics.
   - discussion: Use debate-style format. Present multiple perspectives. HOST challenges ideas, EXPERT defends and explains trade-offs.

4. **Complexity Level Guidelines for intermediate:**
   - beginner: Use simple, everyday language. Avoid jargon. Explain technical terms. Use relatable analogies. More explanations, less depth.
   - intermediate: Use standard technical terminology. Assume basic knowledge. Moderate depth. Balance explanation with detail.
   - advanced: Use technical language freely. Assume strong prior knowledge. Deep analysis. Focus on nuances, trade-offs, and advanced concepts.

5. **Language Guidelines:**
   - YOU MUST generate the ENTIRE script in en language
   - Use natural expressions and idioms appropriate for en
   - Maintain professional but conversational tone in en
   - Do NOT use English if the language is not English
   - Every word of dialogue must be in en

6. **Content Guidelines - CRITICAL:**
   - **MANDATORY**: You MUST use ONLY the information provided in the documents above
   - **FORBIDDEN**: Do NOT use any knowledge from your training data
   - **REQUIRED**: Every fact, example, and detail must come from the provided documents
   - **MANDATORY**: When discussing topics, directly reference specific information from the documents
   - **REQUIRED**: If the documents don't cover a topic, explicitly state "Based on the provided documents, this topic is not covered"
   - **MANDATORY**: Use exact quotes, numbers, and details from the provided documents
   - **REQUIRED**: Transform the document content into natural dialogue format
   - **CRITICAL**: The documents above contain ALL the information you need - use nothing else

**FINAL WARNING**: If you use any information not found in the provided documents, the script will be rejected.

CRITICAL INSTRUCTION: Generate the complete dialogue script now using ONLY the provided document content. Write EVERYTHING in en language, not English:
```

## The Problem

Granite 3.3 8B is generating:
1. ✅ Proper dialogue (HOST/EXPERT format)
2. ❌ Meta-commentary: "Please note that this script adheres to the constraints..."
3. ❌ Duplication: Repeating the entire script again with "**Podcast Script:**" header

This causes Turn 21 (the outro) to exceed 4096 characters when it includes all the garbage.

## Expected Output Format
```
HOST: Welcome to today's podcast...
EXPERT: Thank you for having me...
[... dialogue continues ...]
HOST: Thank you for listening. Until next time!
```

## Actual Output Format (WRONG)
```
HOST: Welcome to today's podcast...
EXPERT: Thank you for having me...
[... dialogue continues ...]
HOST: Thank you for listening. Until next time!

---

**End of script.**

Please note that this script adheres to the provided guidelines, using only the information from the specified documents...

[Instruction's wrapping]:

---

**Podcast Script:**

HOST: Welcome to today's podcast...
[ENTIRE SCRIPT DUPLICATED AGAIN]
```

## Test in WatsonX AI Prompt Studio

Copy the "User Prompt Template" above and test with Granite 3.3 8B Instruct to see if you can get it to generate clean output without the meta-commentary and duplication.

Possible solutions:
1. Add "STOP AFTER THE FINAL HOST LINE. DO NOT ADD ANY COMMENTARY." to prompt
2. Adjust temperature/top_p parameters
3. Use stop sequences: ["**End of script.**", "Please note"]
4. Switch to a larger model (Granite 13B or Llama 3)
