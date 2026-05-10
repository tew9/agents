import gradio as gr
import os
from dotenv import load_dotenv
from research_manager import ResearchManager

load_dotenv()

async def run(query: str):
    async for chunk in ResearchManager().run(query):
        yield chunk
        
with gr.Blocks(theme=gr.themes.Default(primary_hue="orange")) as ui:
    gr.Markdown("# Deep Research Agent")
    gr.Markdown(
        "This is a demo of a deep research agent that can perform research on a given query, write a detailed report, and send it via email."
    )
    query_textbox = gr.Textbox(label="What topic would you like to research?")
    run_button = gr.Button("Run", variant="primary")
    report = gr.Markdown(label="Report")
    
    run_button.click(fn=run, inputs=query_textbox, outputs=report)
    query_textbox.submit(fn=run, inputs=query_textbox, outputs=report)
    
ui.launch(inbrowser=True)