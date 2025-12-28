import React from 'react';
import { motion } from 'framer-motion';
import { User } from '../api';

interface UserSelectorProps {
  users: User[];
  onSelect: (user: User) => void;
}

const UserSelector: React.FC<UserSelectorProps> = ({ users, onSelect }) => {
  const getInitials = (username: string) => {
    return username
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="user-selector"
    >
      <h2>Select a User</h2>
      <div className="user-grid">
        {users.map((user, index) => (
          <motion.div
            key={user.id}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.1 }}
            className="user-card"
            onClick={() => onSelect(user)}
          >
            <div className="user-avatar">
              {user.thumb ? (
                <img src={user.thumb} alt={user.username} />
              ) : (
                getInitials(user.username)
              )}
            </div>
            <div>{user.title || user.username}</div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

export default UserSelector;

