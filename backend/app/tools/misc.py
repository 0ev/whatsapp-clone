def sort_and_convert_to_string(num1, num2):
    # Compare the two numbers and order them with the smaller one first
    smaller, larger = sorted([num1, num2])
    
    # Convert the numbers to string and concatenate them
    return f"chat_{smaller}_{larger}"