DEFAULT_QA_GENERATE_PROMPT_TMPL_EN = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful assistant who needs to generate {num_questions_per_chunk} questions along with their corresponding answers based on the context provided by the user.
Your output should strictly be following this JSON format:

{{"Questions": ["<question1>","<question2>", ...]
"Responses": ["<response1>", "<response2>", ...]}}

Do not add any other notes or explanations to your output beyond the expected dictionary.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{context_str}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

DEFAULT_QA_GENERATE_PROMPT_TMPL_FR = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

Vous êtes un assistant utile qui doit générer {num_questions_per_chunk} questions ainsi que leurs réponses correspondantes basées sur le contexte fourni par l'utilisateur.
Vos questions et réponses doivent toutes être en français.
Votre sortie devrait être dans le format de dictionnaire suivant :

{{"Questions": ["<question1>","<question2>", ...]
"Responses": ["<réponse1>", "<réponse2>", ...]}}

Ne pas ajouter aucune autre note ou explication à votre sortie en dehors du dictionnaire attendu.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{context_str}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

# Hallucination Grader answer,context
FAITHFULNESS_PROMPT_LLAMA3 = (
    """ <|begin_of_text|><|start_header_id|>system<|end_header_id|> You are an evaluation system tasked with evaluating """
    """the faithfulness of a response in regards to provided facts.
you need to assess the factual consistency of the answer.
Define the faithfulness score as:
- High: The answer is completely aligned with the supporting context, without introducing any unsupported claims or misinterpretations.
- Medium:  The answer is mostly aligned with the context but includes minor inaccuracies, omissions, or ambiguities that do not significantly alter the meaning.
- Low: The answer contains major inaccuracies, unsupported claims, or substantial deviations from the supporting context.

Provide your assessment as one unique valid JSON with output schema:
{schema}
<|eot_id|><|start_header_id|>user<|end_header_id|>
Supporting Context:
\n ------- \n
{context}
\n ------- \n

Generated Answer:
{answer}

Your assessment in JSON format:
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
)

# Response Relevance question , answer
ANSWER_RELEVANCE_PROMPT_LLAMA3 = (
    """ <|begin_of_text|><|start_header_id|>system<|end_header_id|> You are an evaluation system tasked with evaluating """
    """the relevance of an answer in regards to question asked.
You are a highly advanced evaluation system specializing in assessing the relevance and factual consistency of answers to given questions.
Your task:
1. Evaluate the relevance of the answer based on the question provided.
2. Assign a relevance score using the following criteria:
   - "High": The answer comprehensively and accurately addresses all aspects of the question.
   - "Medium": The answer partially addresses the question, leaving significant points unanswered or covered vaguely.
   - "Low": The answer fails to address the question effectively, is mostly irrelevant, or contains factual inaccuracies.

Scoring Focus:
- Completeness: Does the answer fully address the question?
- Precision: Is the answer free of unnecessary or redundant information?
- Consistency: Is the answer factually consistent with the given question?

Provide your assessment as one unique valid JSON with output schema:
{schema}
<|eot_id|><|start_header_id|>user<|end_header_id|>
Here is the question:
\n ------- \n
{question}
\n ------- \n
Here is the answer provided to be evaluated:
{answer}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
)


ANSWER_SIMILARITY_EVALUATION_PROMPT_LLAMA3 = """ """


CONTEXT_RELEVANCY_PROMPT_LLAMA3 = (
    """ <|begin_of_text|><|start_header_id|>system<|end_header_id|> You are an evaluation system tasked with evaluating """
    """the relevance of an answer in regards to question asked.
You are a highly advanced evaluation system specializing in assessing the relevancy of retrieved Documents in relation to the user's Question.

Your task:
1. Evaluate how relevant are each retrieved documents for the question that is asked
2. Assign a context relevance score using the following criteria:
   - High: retrieved documents are directly relevant, align closely with the question, and provide precise or substantial information needed to answer the question comprehensively.
   - Medium: retrieved documents are somewhat relevant, containing partial or tangential information that relates to the question but are insufficient for a complete or precise answer.
   - Low: retrieved documents are irrelevant, provide information that does not pertain to the question or are unrelated to the user's intent.

Provide your assessment as one unique valid JSON with output schema:
{schema}
<|eot_id|><|start_header_id|>user<|end_header_id|>
Here is the user's question:
\n ------- \n
{question}
\n ------- \n
retrieved documents:
\n ------- \n
{context}
\n ------- \n
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
)
