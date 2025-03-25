import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import ReactMarkdown from 'react-markdown';

const ChatMessage = ({ message, isUser }) => {
  return (
    <Box sx={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', mb: 2 }}>
      <Paper
        elevation={3}
        sx={{
          p: 2,
          bgcolor: isUser ? 'primary.light' : 'background.paper',
          color: isUser ? 'primary.contrastText' : 'text.primary',
          maxWidth: '80%',
        }}
      >
        {typeof message === 'string' ? (
          <ReactMarkdown>{message}</ReactMarkdown>
        ) : (
          <Typography variant="body1">{JSON.stringify(message, null, 2)}</Typography>
        )}
      </Paper>
    </Box>
  );
};

export default ChatMessage;
