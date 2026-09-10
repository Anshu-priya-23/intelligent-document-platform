# Interview walkthrough

1. Show document-type selection and upload a supported sample. Explain why type is supplied rather than classified.
2. Trace file validation: signature, decode/render, encryption/corruption, byte size and page limit.
3. Explain native extraction versus OCR and orientation. The LLM receives extracted page text with a strict schema and data-only instructions.
4. Open the result: arbitrary fields, comparative periods, table cells, source text and null highlighting. Explain why evidence validation cannot guarantee semantic accuracy.
5. Pick a financial check and calculate the signed variance manually. Show brackets as negatives, each year independently and NOT_APPLICABLE when an operand is missing.
6. Explain the atomic filename upsert. Reprocess the same filename, retrieve via GET, and show one dashboard row and the latest completed result.
7. Show a controlled unsupported-file error and Swagger. Explain dependency errors without exposing provider details or secrets.
8. Walk through tests: real PDF parsing/SQLite/calculations, mocked external LLM boundary. Never describe mocks as live extraction.
9. Show deployment settings and PostgreSQL persistence. Fill live URLs only after real deployment and verification.
10. Discuss limitations: OCR quality, arbitrary layouts, synchronous processing, public demo access, and production improvements.

Before submission, personally read the code, run the tests, configure OCR/provider, compare every output with originals, review the PowerPoint, and complete the README declaration sign-off.
