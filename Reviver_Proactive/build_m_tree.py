import os
from dotenv import load_dotenv
from pre_processor import Photo_PreProcessor


if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    Processor = Photo_PreProcessor(api_key, "cw_1", has_meta_data=True, old_mtree_file="memory_tree.json")

    # Processor.batch_photo_extraction(1, 43)
    # Processor.save_m_tree()

    # Processor.slice()

    slice_locs = [1,7,14,21,23,33,36,41,44]
    Processor.build_m_tree(slice_locs)