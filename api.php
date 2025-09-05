<?php
session_start();

// Configuration
$uploadDir = 'uploads/';
$usersFile = 'users.json';
$loginAttemptsFile = 'login_attempts.log';

// Create directories if they don't exist
if (!file_exists($uploadDir)) {
    mkdir($uploadDir, 0777, true);
}

// Load users from file
$users = [];
if (file_exists($usersFile)) {
    $users = json_decode(file_get_contents($usersFile), true);
}

// Handle API requests
$action = $_POST['action'] ?? $_GET['action'] ?? '';

// Set response header
header('Content-Type: application/json');

switch ($action) {
    case 'login':
        handleLogin();
        break;
    case 'upload':
        handleUpload();
        break;
    case 'listFiles':
        handleListFiles();
        break;
    case 'deleteFile':
        handleDeleteFile();
        break;
    default:
        echo json_encode(['success' => false, 'message' => 'Invalid action']);
        break;
}

function handleLogin() {
    global $users, $loginAttemptsFile;
    
    $data = json_decode(file_get_contents('php://input'), true);
    $username = $data['username'] ?? '';
    $password = $data['password'] ?? '';
    
    // Log login attempt
    $logEntry = date('Y-m-d H:i:s') . " - Login attempt for username: $username\n";
    file_put_contents($loginAttemptsFile, $logEntry, FILE_APPEND);
    
    // Check if user exists and is approved
    if (isset($users[$username]) && $users[$username]['password'] === $password && $users[$username]['approved']) {
        // Generate a simple token (in production, use a more secure method)
        $token = md5($username . time());
        
        // Store token in session (or in a database in production)
        $_SESSION['tokens'][$token] = $username;
        
        echo json_encode([
            'success' => true,
            'token' => $token
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'message' => 'Invalid username or password, or account not approved yet.'
        ]);
    }
}

function handleUpload() {
    global $uploadDir;
    
    // Validate token
    $token = $_POST['token'] ?? '';
    $username = validateToken($token);
    
    if (!$username) {
        echo json_encode(['success' => false, 'message' => 'Invalid token']);
        return;
    }
    
    // Create user directory if it doesn't exist
    $userDir = $uploadDir . $username . '/';
    if (!file_exists($userDir)) {
        mkdir($userDir, 0777, true);
    }
    
    // Handle file upload
    if (isset($_FILES['file'])) {
        $fileName = basename($_FILES['file']['name']);
        $targetFilePath = $userDir . $fileName;
        
        // Check if file already exists
        if (file_exists($targetFilePath)) {
            echo json_encode(['success' => false, 'message' => 'File already exists.']);
            return;
        }
        
        if (move_uploaded_file($_FILES['file']['tmp_name'], $targetFilePath)) {
            echo json_encode(['success' => true, 'message' => 'File uploaded successfully.']);
        } else {
            echo json_encode(['success' => false, 'message' => 'Error uploading file.']);
        }
    } else {
        echo json_encode(['success' => false, 'message' => 'No file uploaded.']);
    }
}

function handleListFiles() {
    global $uploadDir;
    
    // Validate token
    $data = json_decode(file_get_contents('php://input'), true);
    $token = $data['token'] ?? '';
    $username = validateToken($token);
    
    if (!$username) {
        echo json_encode(['success' => false, 'message' => 'Invalid token']);
        return;
    }
    
    // Get user files
    $userDir = $uploadDir . $username . '/';
    $files = [];
    
    if (file_exists($userDir)) {
        $dirFiles = scandir($userDir);
        foreach ($dirFiles as $file) {
            if ($file !== '.' && $file !== '..') {
                $filePath = $userDir . $file;
                $files[] = [
                    'name' => $file,
                    'path' => $filePath,
                    'size' => filesize($filePath),
                    'modified' => filemtime($filePath)
                ];
            }
        }
    }
    
    echo json_encode(['success' => true, 'files' => $files]);
}

function handleDeleteFile() {
    global $uploadDir;
    
    // Validate token
    $data = json_decode(file_get_contents('php://input'), true);
    $token = $data['token'] ?? '';
    $filename = $data['filename'] ?? '';
    $username = validateToken($token);
    
    if (!$username) {
        echo json_encode(['success' => false, 'message' => 'Invalid token']);
        return;
    }
    
    // Delete file
    $userDir = $uploadDir . $username . '/';
    $filePath = $userDir . basename($filename);
    
    if (file_exists($filePath) && is_file($filePath)) {
        if (unlink($filePath)) {
            echo json_encode(['success' => true, 'message' => 'File deleted successfully.']);
        } else {
            echo json_encode(['success' => false, 'message' => 'Error deleting file.']);
        }
    } else {
        echo json_encode(['success' => false, 'message' => 'File not found.']);
    }
}

function validateToken($token) {
    // Check if token exists in session
    if (isset($_SESSION['tokens'][$token])) {
        return $_SESSION['tokens'][$token];
    }
    return false;
}
?>