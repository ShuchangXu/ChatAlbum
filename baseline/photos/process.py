
with open("./photo_description.txt", 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
with open("./result.txt", 'w', encoding='utf-8') as f:
    for i, line in enumerate(lines):
        line = str(i+100) + '\t' + line
        f.write(line)
    