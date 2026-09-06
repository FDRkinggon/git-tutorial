import {templatePlace} from './defaultTemplates.js'
import { dataArr } from './dataField.js'

let container = document.querySelector('body')
function loppFunc(dataArr = [templatePlace]){
  const loopingHere = dataArr.map(loop => {
    const {image, location, price, description, size} = loop
    return  `
    <div class="container">
      <div class="image-container">
        <img src="${image}" alt="anime facial">
      </div>
      <div class="content">
          <p>${location}</p>
          <p>$ ${price}</p>
          <p>${description}</p>
          <p>${size}</p>
      </div>
    </div>
  `;}).join('')
  return loopingHere
}


container.innerHTML = loppFunc(dataArr)