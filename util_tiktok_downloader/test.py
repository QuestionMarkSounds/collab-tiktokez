
import os
from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    api_key="sk-proj-0U1etEdNPyfN0tEvklyVT3BlbkFJ0899XXITmyGhvlsfA7eS",
)

stream = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "hello how are you"}],
    stream=True,
)

buffer = ""
for chunk in stream:
    content = chunk.choices[0].delta.content
    if content is not None: buffer += content

    print(buffer)
    