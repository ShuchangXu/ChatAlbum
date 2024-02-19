import os
from dotenv import load_dotenv
from pre_processor import Photo_PreProcessor


if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    Processor = Photo_PreProcessor(api_key, "lmq_1", "memory_tree.json")
    Processor.slice()
    # Processor.batch_photo_extraction(1, 56)

    # Processor.save_m_tree()