import os
from dotenv import load_dotenv
from pre_processor import Photo_PreProcessor


if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    Processor = Photo_PreProcessor(api_key, "zhy_1", "memory_tree.json")

    # Processor.batch_photo_extraction(1, 33)
    # Processor.save_m_tree()

    # Processor.slice()

    slice_locs = [1,2,6,8,11,15,17,21,26,33,33]
    Processor.build_m_tree(slice_locs)