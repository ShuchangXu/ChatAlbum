import os
from dotenv import load_dotenv
from pre_processor import Photo_PreProcessor


if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    Processor = Photo_PreProcessor(api_key, "wmq_1")
    
    event_extraction_guide = open("./prompts/photo_event_guide", 'r', encoding='utf-8').read()
    des_extraction_guide = open("./prompts/photo_des_guide", 'r', encoding='utf-8').read()
    

    for i in range(1, 30):
        reply= Processor.visual_question_answer("",i)
        # Processor.save_reply(reply, photo_name)