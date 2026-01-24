class WordInfo():
    def __init__(self):
        self.not_in_word = [];
        self.in_word_but_not_at = [];
        self.in_word_at = ["?", "?", "?", "?", "?"]
        self.not_in_word_at = [];
    def register_guess(self, guess, result):
        for i, char in enumerate(guess):
            if result[i] == "0":
                self.not_in_word.append(char);
                add = (char, i);
                self.not_in_word_at.append(add);
            elif result[i] == "1":
                add = (char, i)
                self.in_word_but_not_at.append(add);
            elif result[i] == "2" or result[i] == "3":
                self.in_word_at[i] = char;
            for char in self.in_word_at:
                if char in self.not_in_word:
                    self.not_in_word.remove(char);
            in_word_somewhere = [pair[0] for pair in self.in_word_but_not_at];
            for char in in_word_somewhere:
                if char in self.not_in_word:
                    self.not_in_word.remove(char);
    def is_valid(self, candidate):
        for char in self.not_in_word:
            if char in candidate:
                # if "e" in candidate:
                    # print("removing " + candidate + " on grounds of letter in word that shoudn't be"); 
                return False;
        for pair in self.in_word_but_not_at:
            if not pair[0] in candidate:
                # print("removing " + candidate + " on grounds of letter not in word that should be at some position"); 
                return False
        for i, char in enumerate(candidate):
            for pair in self.in_word_but_not_at:
                if char == pair[0] and i == pair[1]:
                    # print("removing " + candidate + " on grounds of letter in word at wrong position")
                    return False
            for pair in self.not_in_word_at:
                if char == pair[0] and i == pair[1]:
                    return False;
                    # print("removing " + candidate + " on grounds of letter definitely shouldn't be in that spot")
            must_be = self.in_word_at[i];
            if char != must_be and must_be != "?":
                # print("removing " + candidate + " on grounds of doesn't have correct letter in correct spot")
                return False;
        return True;
    def cleanse(self, word_list):
        res = [];
        for word in word_list:
            if self.is_valid(word):
                res.append(word)
        return res
    def is_word_complete(self):
        return not "?" in self.in_word_at;
    def get_best_guess(self):
        return "".join(self.in_word_at);

def get_response(word, guess):
    used_letters = [];
    res = ["?", "?", "?", "?", "?"]
    for i in range(len(guess)):
        if guess[i] == word[i]:
            res[i] = "2"
            used_letters.append(guess[i])
    # Check for yellow letters
    for i in range(len(guess)):
        if res[i] == "?" and guess[i] in word:
            res[i] = "1";
        if res[i] == "2" and word.count(guess[i]) > 1:
            res[i] = '3';
    for i in range(len(guess)):
        if res[i] == "?":
            res[i] = "0";
    return "".join(res)

def sort_by_letter_frequency(words):
    frequencies = [];
    for i in range(5):
        frequencies.append([]);
        for ii in range(26):
            frequencies[i].append(0);
    for word in words:
        # print(word)
        for i, char in enumerate(word):
            # print(char)
            frequencies[i][ord(char) - 97] += 1;
        scores = []
    for word in words:
        score = 0;
        valid = True
        for i, char in enumerate(word):
            score += frequencies[i][ord(char) - 97];
        # if valid:
        scores.append((word, score));
    scores.sort(key=lambda x: x[1], reverse = True)
    
    return [pair[0] for pair in scores]