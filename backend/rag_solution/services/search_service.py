from rag_solution.schemas.search_schema import SearchInput, SearchOutput

class SearchService:
    
    def question_llm(self, search_input: SearchInput) -> SearchOutput:
        return SearchOutput(generated_answer = "[INPUT QUESTION] " + input.question)
