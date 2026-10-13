# Split text into chunks

from langchain_text_splitters import RecursiveCharacterTextSplitter


splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150
)


def create_chunks(text):

    return splitter.split_text(text)
#chunk_size = 600–1000 characters
#overlap = 100–200 characters