import React, {useEffect, useState} from 'react'
import axios from 'axios'

export default function Products(){
  const [products, setProducts] = useState([])
  useEffect(()=>{
    axios.get('/api/products').then(r=>setProducts(r.data)).catch(()=>setProducts([]))
  },[])
  return (
    <div>
      <h2>Products</h2>
      <ul>
        {products.map(p=> (
          <li key={p.id}>{p.title} — ${p.price}</li>
        ))}
      </ul>
    </div>
  )
}
