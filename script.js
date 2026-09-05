import {templatePlace} from './defaultTemplates.js'
let imgEl = document.getElementById('img-dsp')
let locationEl = document.getElementById('location-el')
let amountEl = document.getElementById('amount-el')
let descriptionEl = document.getElementById('description-el')
let sizeEl = document.getElementById('size-el')


const {image, location, price, description, size} = templatePlace

imgEl.src = image
locationEl.textContent = location
amountEl.textContent = `$${price}`
descriptionEl.textContent = description
sizeEl.textContent = `${size} m^2`