import React, { useState, useEffect } from 'react';
import api from '../api';
import '../styles/Common.css';

function Profile() {
  const [profile, setProfile] = useState(null);
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');

  useEffect(() => {
    api.get('/profiles/my_profile/').then((res) => {
      setProfile(res.data);
      setPhone(res.data.phone || '');
      setAddress(res.data.address || '');
      setCity(res.data.city || '');
    }).catch(() => alert('Failed to load profile'));
  }, []);

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/profiles/${profile.id}/`, { phone, address, city });
      alert('Profile updated');
    } catch (err) {
      alert('Failed to update profile');
    }
  };

  if (!profile) return <div className="container">Loading...</div>;

  return (
    <div className="container">
      <h1>My Profile</h1>
      <form onSubmit={handleUpdate}>
        <div className="form-group">
          <label>Email</label>
          <input type="email" value={profile.user?.email} disabled />
        </div>
        <div className="form-group">
          <label>Role</label>
          <input type="text" value={profile.role} disabled />
        </div>
        <div className="form-group">
          <label>Phone</label>
          <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Address</label>
          <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} />
        </div>
        <div className="form-group">
          <label>City</label>
          <input type="text" value={city} onChange={(e) => setCity(e.target.value)} />
        </div>
        <button type="submit">Update Profile</button>
      </form>
    </div>
  );
}

export default Profile;
