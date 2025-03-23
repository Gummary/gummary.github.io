---
title: "Tokenization介绍"
slug: Tokenization介绍
date: 2025-03-17T23:29:00+08:00
draft: false
---

<!--more-->

## 序言

在谈到 Large Language Model（LLM）大模型时，离不开的一个概念就是 token，因为几乎所有生成式的大模型服务商基本都通过 token 数量来计费。第一次接触 token 的时候，我以为 token 是一个字或者一个单词，但实际使用时二者又不是完全相等的关系，这篇博客就主要看下 token 究竟什么，并介绍了当前生成式大语言模型所用的BPE算法。

## 从 Tokenization 说起

一篇文章在输入给大模型之前，首先需要经过 Tokenization，也即将输入的句子转为 token 序列。

## 为什么需要 Tokenization

对文本进行 tokenization 的原因是为了让计算机能够理解一句话背后所代表的含义。

为了让计算机能理解，一种简单的方式是，人工预定义一些句子并直接设定计算机要做出的反应。

```
[
{"Question":"你好",
"Answer":"你好"},
{"Question":"你叫什么名字",
"Answer":"我叫小美"},
]
```

但人类的语言丰富多变，这种方式显然是不现实的。但无论语言如何多变，其背后一定存在着某些规则，否则人类也无法理解语言背后的含义。所以我们也想让机器知道这些规则，通过这些规则来解析句子，进而理解句子背后的含义。

对于一门语言来说，主要组成部分包括语音、单词和语法，其中单词是组成句子的基本单元，语法则是语言如何组织单词的规则。所以如果计算机只处理文本，并且理解了单词含义及对应的语法规则，理解人类语言就成为了可能。

Tokenization 所做的就是第一步，将句子拆分成单词，让计算机学习单词的含义。

## 如何做 Tokenization

我们先看英文的情况，对于英文来说，天然的用空格作为了单词与单词之间的间隔符，所以很容易想到的就是使用空格进行分词。

```
The quick brown fox jumped over the lazy dog
```

使用空格分词后，可得到如下的词表:

```python
['brown', 'quick', 'the', 'fox', 'dog.', 'jumped', 'over', 'The', 'lazy']
```

这种分词方法非常简单，但问题也很明显：

1. 这种处理方式会要求计算机要有一个非常巨大的词表，并且每当出现新的单词时，都要加入到词表中，否则计算就无法处理。例如计算机无法识别到 dataset 是 data 和 set 的组合、无法学习到 she's、he's、it's 背后的's 缩写。
2. 无法处理无分割符的语言，如中文、日文等。

既然无法单词粒度太粗，那我们可以将粒度拆的再细点。无论是什么语言，在计算机中都是特定格式的字符序列，如 ascii、utf-8 等。所以我们可以将 token 的粒度拆分到字符维度。得到

```python
['p', 'z', 'r', 'y', 'o', 'l', 'b', 'd', 'm', 'g', ' ', 'f', 'q', 'v', 'h', 'i', 'c', 'j', 'T', 'e', 't', 'a', 'w', '.', 'n', 'k', 'u', 'x']
```

相比于单词唯独来说，使用字符维度的 token 方法可以更好的处理未知的词汇，而且也可以处理无分隔符的语言。

但这种划分方式也有其缺点，首先就是生成的 token 太多了，越多的 token 所需的计算量越大。其次就是在字符维度，计算机无法学习到其本身的语义信息。

所以科研人员开始寻找一种介于单词和字符中间的一种 token 方式，subword tokenization，这是目前主流大语言模型所使用的 token 方式。

### subword tokenization

subword tokenization 是为了解决，word 级别词表过大的问题，及字符级别输入过长且无语义的问题。其主要步骤是，将单词拆成一些更有意义的单元。例如，-ing，un-，-ily，-ed,-'s 等等。这样，当遇到未知的单词时，也可处理，例如如果词表中有 foot 和 ball，遇到 football 时，可以将其拆分成 foot-和-ball 两个 token。

使用这种方式，不需要将每一个遇到的单词都加到词表中，解决了词表过大的问题；同时，单词又没有拆分出非常多 token 且每个 token 都有一定的语义信息，解决了字符级别序列特别长且无语义的问题。

目前 subword tokenization 的主要方式有三种：BPE (GPT-2), WordPiece (BERT), and Unigram (T5)

#### BPE

bpe 是构建一个词汇表，词汇表中是可能出现的字词。

BPE 是一种起源于文本压缩的算法，现在被用于大模型训练中，期望用最少的 token 表示更多文本。

BPE 处理英文文本的主要步骤如下：

1. 将文库按空格分词，在每个单词的后面拼接一个特殊 token`</s>`，单词内的每个字符都作为一个单独的 token，构建出基础的词库
2. 统计词库内每个 token 出现的次数
3. 计算每个单词内相邻两个 token 出现的频率，选出最高的 token pair 加入到词库中，合并单词内的 token pair
4. 重复 2-3 步

在每个单词末尾添加一个特殊 token 的原因是，在英文语境下，同一个 sub-word 在词尾和其他位置可能有不同的含义。例如 easiest 中的 st 和 star 中的 st。

代码实现如下

```python
def get_vocabulary(text: str) -> Dict[str, int]:  
    vocab = defaultdict(int)  
    for l in text.split('\n'):  
        for word in l.strip().split():  
            vocab[' '.join([c for c in word]) + ' </s>'] += 1  
    return vocab
```

输出为：

```
{'T h e </s>': 1, 'h i g h e s t </s>': 1, 'm o u n t a i n </s>': 1, 'a l s o </s>': 1, 'i s </s>': 1, 't h e </s>': 2, 'c o o l e s t </s>': 1, 'i n </s>': 1, 'w o r l d . </s>': 1}
```

基于这个初始词表，统计每个出现次数最多的两个相邻token


```python
def count_token_pair_frequency(vocab: Dict[str, int]):  
    frequency = defaultdict(int)  
    for word, freq in vocab.items():  
        w = word.split()  
        for i in range(len(w) - 1):  
            frequency[(w[i], w[i + 1])] += freq  
    return frequency
```


```
{('T', 'h'): 1, ('h', 'e'): 4, ('e', '</s>'): 3, ('h', 'i'): 1, ('i', 'g'): 1, ('g', 'h'): 1, ('e', 's'): 2, ('s', 't'): 2, ('t', '</s>'): 2, ('m', 'o'): 1, ('o', 'u'): 1, ('u', 'n'): 1, ('n', 't'): 1, ('t', 'a'): 1, ('a', 'i'): 1, ('i', 'n'): 2, ('n', '</s>'): 2, ('a', 'l'): 1, ('l', 's'): 1, ('s', 'o'): 1, ('o', '</s>'): 1, ('i', 's'): 1, ('s', '</s>'): 1, ('t', 'h'): 2, ('c', 'o'): 1, ('o', 'o'): 1, ('o', 'l'): 1, ('l', 'e'): 1, ('w', 'o'): 1, ('o', 'r'): 1, ('r', 'l'): 1, ('l', 'd'): 1, ('d', '.'): 1, ('.', '</s>'): 1}
```

统计这个词表中出现次数最多的token pair为('h', 'e')，出现了4次，这就是一个merge rule，将其引用到原始词表中

```python
def merge_token_pair(pair: Tuple[str, str], vocab: Dict[str, int]) -> Dict[str, int]:  
    new_vocab = defaultdict(int)  
    bigram = " ".join(pair)  
    # (?<!\S) 是一个负向后行断言，表示匹配的位置前面不能是一个非空白字符。  
    # (?!\S) 是一个负向前瞻断言，表示匹配的位置后面不能是一个非空白字符。  
    # 这个正则表达式模式的作用是匹配那些前后都是空白字符的二元组。  
    p = re.compile(r'(?<!\S)' + bigram + r'(?!\S)')  
  
    for word in vocab.keys():  
        w = p.sub(''.join(pair), word)  
        new_vocab[w] = vocab[word]  
    return new_vocab
```


```
{'T he </s>': 1, 'h i g he s t </s>': 1, 'm o u n t a i n </s>': 1, 'a l s o </s>': 1, 'i s </s>': 1, 't he </s>': 2, 'c o o l e s t </s>': 1, 'i n </s>': 1, 'w o r l d . </s>': 1}
```

不断重复统计-合并的步骤一定次数，即可得到最终的词表，最终代码如下：

```python

def get_tokens(vocab: Dict[str, int]):  
    tokens = defaultdict(int)  
    for word, freq in vocab.items():  
        for token in word.split():  
            tokens[token] += freq  
    return tokens

def get_vocabulary(text: str) -> Dict[str, int]:  
    vocab = defaultdict(int)  
    for l in text.split('\n'):  
        for word in l.strip().split():  
            vocab[' '.join([c for c in word]) + ' </s>'] += 1  
    return vocab

def count_token_pair_frequency(vocab: Dict[str, int]):  
    frequency = defaultdict(int)  
    for word, freq in vocab.items():  
        w = word.split()  
        for i in range(len(w) - 1):  
            frequency[(w[i], w[i + 1])] += freq  
    return frequency

def merge_token_pair(pair: Tuple[str, str], vocab: Dict[str, int]) -> Dict[str, int]:  
    new_vocab = defaultdict(int)  
    bigram = " ".join(pair)  
    # (?<!\S) 是一个负向后行断言，表示匹配的位置前面不能是一个非空白字符。  
    # (?!\S) 是一个负向前瞻断言，表示匹配的位置后面不能是一个非空白字符。  
    # 这个正则表达式模式的作用是匹配那些前后都是空白字符的二元组。  
    p = re.compile(r'(?<!\S)' + bigram + r'(?!\S)')  
  
    for word in vocab.keys():  
        w = p.sub(''.join(pair), word)  
        new_vocab[w] = vocab[word]  
    return new_vocab


def start_iter(corpus, iter_times):  
    vocab = get_vocabulary(corpus)  
    tokens = get_tokens(vocab=vocab)  
    print("BEFORE BPE TOKENS: {}".format(tokens))  
    for i in range(iter_times):  
        freq = count_token_pair_frequency(vocab=vocab)  
        new_rule = max(freq, key=freq.get)  
        print(f'Iter {i} get merge rule: {new_rule}')  
        vocab = merge_token_pair(pair=new_rule, vocab=vocab)  
    tokens = get_tokens(vocab=vocab)  
    print("AFTER BPE TOKENS: {}".format(tokens))  
  
  
TEST_CORPUS = "The highest mountin also is the coolest in the world."  
start_iter(TEST_CORPUS, 10)


```


在对语料库学习后，即可对句子进行编解码。编码的过程就是先将所有token按长度从大到小排列，然后对句子进行编码。

```python
def encode(corpus: str, tokens: List[str]):  
    words = [w + '</s>' for w in corpus.strip().split()]  
    for i in range(len(words)):  
        words[i] = encode_word(words[i], tokens)  
  
    return ' '.join([sub_word for word in words for sub_word in word])  
  
  
def encode_word(word: str, tokens: List[str]):  
    if len(word) == 0:  
        return []  
  
    sorted_tokens = sorted(tokens, key=len, reverse=True)  
    for token in sorted_tokens:  
        if len(token) > len(word):  
            continue  
        i = word.find(token)  
        if i == -1:  
            continue  
  
        return encode_word(word[:i], tokens) + [token] + encode_word(word[i + len(token):], tokens=tokens)  
    return [word]  
  
corpus = "helloworldhahaha hello word"  
tokens = ['he', 'll', 'world', 'ha']  
print(encode(corpus, tokens))
```

```
he ll o world ha ha ha </s> he ll o</s> word</s>
```

而解码的过程就非常简单了，将句子按`</s>`分割后，将每个token合并即可。


## 参考

1. [BPE实现](https://leimao.github.io/blog/Byte-Pair-Encoding/)
2. [tokenizer库](https://huggingface.co/docs/tokenizers/en/quicktour#post-processing)
3. [token时新增特殊token](https://discuss.huggingface.co/t/gpt2tokenizer-not-putting-bos-eos-token/27394)
4. [基于已有的tokenizer训练](https://huggingface.co/learn/nlp-course/en/chapter6/2?fw=pt)
5. [tokenizer和transformer的tokenizer](https://stackoverflow.com/questions/76045605/using-a-custom-trained-huggingface-tokenizer)
6. [tokenizer中文教程](https://zhuanlan.zhihu.com/p/657047389)
7. [小王子英文版](https://github.com/yanranzhao/n-gram-language-identification/blob/master/en-the-little-prince.txt)
