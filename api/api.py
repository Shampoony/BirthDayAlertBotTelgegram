from requests import get
from random import randint
from bs4 import BeautifulSoup

page = randint(1, 10)
link = f'https://www.pozdravok.com/pozdravleniya/den-rozhdeniya/proza-{page}.htm'

def get_birthday_congratulation():
    response = get(link)
    
    if response.status_code != 200:
        print(f"Ошибка доступа: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    elements = soup.find_all(class_='sfst')  


    
    if len(elements):
        randind = randint(0, len(elements)-1)
        return elements[randind].text
    else:
        return "Элемент с таким классом не найден"

# Тест
if __name__ == "__main__":
    congratulation = get_birthday_congratulation()
    print(congratulation)
