"use strict";

let addButton = document.querySelector('#create_point');
const lastCity = document.querySelector('.end_block');
const ourForm = document.querySelector('form');

addButton.addEventListener("click", (e) => {
    let newCityContainer = document.createElement('div');
    newCityContainer.innerHTML = '<label for="extra_city">Дополнительная точка:</label><input type="text" name="extra_city" required>'

    newCityContainer.classList.add('form-block');
    newCityContainer.classList.add('added-city');

    ourForm.insertBefore(newCityContainer, lastCity);
});