import React, {useState} from 'react'
import axios from 'axios'

export default function Login(){
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [token,setToken]=useState(null)
  const submit = async (e)=>{
    e.preventDefault()
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    const res = await axios.post('/api/auth/token', form)
    setToken(res.data.access_token)
    localStorage.setItem('token', res.data.access_token)
  }
  return (
    <div>
      <h2>Login</h2>
      <form onSubmit={submit}>
        <input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} />
        <input placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
        <button>Login</button>
      </form>
      {token && <div>Logged in</div>}
    </div>
  )
}
