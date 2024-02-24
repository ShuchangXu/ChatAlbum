import os
from dotenv import load_dotenv
from pre_processor import Photo_PreProcessor


if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    Processor = Photo_PreProcessor(api_key, "lmq_2", has_meta_data=True, old_mtree_file="memory_tree.json")

    # Processor.batch_photo_extraction(1, 53)
    # Processor.save_m_tree()

    # Processor.slice()

    slice_locs = [1,5,11,18,21,23,27,36,41,50,54]
    Processor.build_m_tree(slice_locs)