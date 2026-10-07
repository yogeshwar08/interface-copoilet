from app.llm.gemini import llm


def main():
    query = "What are the diagnostic criteria?"

    context = """
[Source 1]
Document: 01_Diabetes_Clinical_Guideline.pdf
Page: 1

A diagnosis of Type 2 Diabetes Mellitus should be confirmed
using one of the following criteria:

Fasting Plasma Glucose (FPG) >= 126 mg/dL (7.0 mmol/L)

Oral Glucose Tolerance Test (2-hour, 75g load)
>= 200 mg/dL (11.1 mmol/L)

HbA1c >= 6.5%

Random Plasma Glucose >= 200 mg/dL with classic symptoms.
"""

    answer = llm.generate(
        query=query,
        context=context,
    )

    print("\n=== GEMINI RESPONSE ===")
    print(answer)


if __name__ == "__main__":
    main()
