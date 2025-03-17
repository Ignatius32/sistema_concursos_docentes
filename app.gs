// IMPORTANT: Make sure to add GOOGLE_DRIVE_SECURE_TOKEN in Script Properties with the value from your .env file

// Template IDs for document generation
// Add your actual template document IDs here
const TEMPLATES = {
  'concursoResolucion': '1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', // Replace with actual template ID
  'actaSustanciacion': '1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',  // Replace with actual template ID
  'certificadoPostulante': '1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', // Replace with actual template ID
  'resLlamadoTribunalInterino': '1Sb8TI4AJM6bIu-I-xGB-44ST6AltcQwIGZyN6F-sKHc', // 
  'resLlamadoRegular': '1Eg0N5s4H_wGEHUZClYZs-jF4ED2pjHbT-KsUoSSLOX8',
  'resTribunalRegular': '119a255YfBWEdqu_IEJT1vYWSLAP9KhVk4G5NHPTYD6Q',
  // Add more templates as needed
};

// Utility functions
function sanitizeFolderName(name) {
  // First normalize accented characters
  const normalized = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  // Then replace any remaining invalid characters with underscore
  return normalized.replace(/[^a-z0-9]/gi, '_');
}

function verifyToken(token) {
  var scriptProperties = PropertiesService.getScriptProperties();
  var validToken = scriptProperties.getProperty('GOOGLE_DRIVE_SECURE_TOKEN');
  return token === validToken;
}

// Function to create a document from template
function createDocFromTemplate(templateName, data, targetFolderId, fileName) {
  // Basic validation
  if (!templateName || !data || !targetFolderId || !fileName) {
    throw new Error("Template name, data, target folder ID, and file name are required.");
  }
  
  // Get template ID from the mapping
  var templateId = TEMPLATES[templateName];
  if (!templateId) {
    throw new Error(`Unknown template: ${templateName}`);
  }
  
  try {
    // Get the template file
    var templateFile = DriveApp.getFileById(templateId);
    
    // Get the target folder
    var targetFolder = DriveApp.getFolderById(targetFolderId);
    
    // Create a copy of the template in the target folder
    var newDoc = templateFile.makeCopy(fileName, targetFolder);
    
    // Open the document for editing
    var doc = DocumentApp.openById(newDoc.getId());
    var body = doc.getBody();
    
    // Replace all placeholders with actual data
    Object.keys(data).forEach(function(key) {
      var placeholder = '<<' + key + '>>';
      body.replaceText(placeholder, data[key] || '');
    });
    
    // Save and close the document
    doc.saveAndClose();
    
    return {
      fileId: newDoc.getId(),
      webViewLink: newDoc.getUrl()
    };
  } catch (err) {
    throw new Error("Error creating document from template: " + err.message);
  }
}

// Function to create a contest folder under a specific root folder.
function crearConcurso(folderName) {
  // Basic validation
  if (!folderName) {
    throw new Error("Folder name is required.");
  }

  // Sanitize the folder name
  var sanitizedName = sanitizeFolderName(folderName);
  
  // Your folder ID from the Google Drive URL
  var root = DriveApp.getFolderById("1BD6fp88EQTwW9yhw4USkJjaRlbmeSHHa");
  
  // Check if a folder with the same name already exists.
  var folders = root.getFoldersByName(sanitizedName);
  if (folders.hasNext()) {
    throw new Error("Folder already exists.");
  }
  
  // Create the new folder with sanitized name
  var newFolder = root.createFolder(sanitizedName);
  
  return {
    folderId: newFolder.getId()
  };
}

// Function to create a nested folder inside a parent folder
function createNestedFolder(parentFolderId, folderName) {
  // Get parent folder
  var parentFolder = DriveApp.getFolderById(parentFolderId);
  
  // Sanitize folder name
  var sanitizedName = sanitizeFolderName(folderName);
  
  // Check if folder already exists
  var folders = parentFolder.getFoldersByName(sanitizedName);
  if (folders.hasNext()) {
    throw new Error("Folder already exists.");
  }
  
  // Create new folder
  var newFolder = parentFolder.createFolder(sanitizedName);
  return newFolder.getId();
}

// Function to create a postulante folder inside a concurso folder
function crearPostulante(concursoFolderId, folderName) {
  // Basic validation
  if (!concursoFolderId || !folderName) {
    throw new Error("Concurso folder ID and folder name are required.");
  }

  // Sanitize the folder name
  var sanitizedName = sanitizeFolderName(folderName);
  
  // Get the concurso folder
  var concursoFolder = DriveApp.getFolderById(concursoFolderId);
  
  // Check if a folder with the same name already exists
  var folders = concursoFolder.getFoldersByName(sanitizedName);
  if (folders.hasNext()) {
    throw new Error("Folder already exists.");
  }
  
  // Create the new folder with sanitized name inside the concurso folder
  var newFolder = concursoFolder.createFolder(sanitizedName);
  return newFolder.getId();
}

// Function to upload a file to a specific folder
function uploadFile(folderId, fileName, fileData) {
  // Basic validation
  if (!folderId || !fileName || !fileData) {
    throw new Error("Folder ID, file name and file data are required.");
  }

  try {
    // Get the folder
    var folder = DriveApp.getFolderById(folderId);
    
    // Convert base64 data to bytes
    var decodedData = Utilities.base64Decode(fileData);
    var blob = Utilities.newBlob(decodedData, "application/pdf", fileName);
    
    // Create the file in Drive
    var file = folder.createFile(blob);
    
    return {
      fileId: file.getId(),
      webViewLink: file.getUrl()
    };
  } catch (err) {
    throw new Error("Error uploading file: " + err.message);
  }
}

// Function to delete a file from Drive
function deleteFile(fileId) {
  // Basic validation
  if (!fileId) {
    throw new Error("File ID is required.");
  }

  try {
    // Get the file and delete it
    var file = DriveApp.getFileById(fileId);
    file.setTrashed(true);
    return true;
  } catch (err) {
    throw new Error("Error deleting file: " + err.message);
  }
}

// Function to delete a folder from Drive
function deleteFolder(folderId) {
  // Basic validation
  if (!folderId) {
    throw new Error("Folder ID is required.");
  }

  try {
    // Get the folder and delete it
    var folder = DriveApp.getFolderById(folderId);
    folder.setTrashed(true);
    return true;
  } catch (err) {
    throw new Error("Error deleting folder: " + err.message);
  }
}

// Function to overwrite an existing file
function overwriteFile(fileId, fileData) {
  // Basic validation
  if (!fileId || !fileData) {
    throw new Error("File ID and file data are required.");
  }

  try {
    // Get the existing file
    var existingFile = DriveApp.getFileById(fileId);
    var fileName = existingFile.getName();
    var parentFolder = existingFile.getParents().next();
    
    // Delete the existing file
    existingFile.setTrashed(true);
    
    // Convert base64 data to bytes
    var decodedData = Utilities.base64Decode(fileData);
    var blob = Utilities.newBlob(decodedData, "application/pdf", fileName);
    
    // Create the new file in the same folder
    var newFile = parentFolder.createFile(blob);
    
    return {
      fileId: newFile.getId(),
      webViewLink: newFile.getUrl()
    };
  } catch (err) {
    throw new Error("Error overwriting file: " + err.message);
  }
}

// Function to rename a folder in Drive
function renameFolder(folderId, newName) {
  // Basic validation
  if (!folderId || !newName) {
    throw new Error("Folder ID and new name are required.");
  }

  // Sanitize the new folder name
  var sanitizedName = sanitizeFolderName(newName);

  try {
    // Get the folder and rename it
    var folder = DriveApp.getFolderById(folderId);
    folder.setName(sanitizedName);
    return true;
  } catch (err) {
    throw new Error("Error renaming folder: " + err.message);
  }
}

// Function to handle HTTP requests
function doPost(e) {
  try {
    // Parse request data
    var data = JSON.parse(e.postData.contents);
    
    // Verify token
    if (!data.token || !verifyToken(data.token)) {
      throw new Error("Invalid token");
    }
    
    // Handle different actions
    switch (data.action) {
      case "createFolder":
        return handleCreateFolder(data);
      case "createNestedFolder":
        return handleCreateNestedFolder(data);
      case "createPostulanteFolder":
        return handleCreatePostulanteFolder(data);
      case "createDocFromTemplate":
        return handleCreateDocFromTemplate(data);
      case "uploadFile":
        return handleUploadFile(data);
      case "deleteFile":
        return handleDeleteFile(data);
      case "deleteFolder":
        return handleDeleteFolder(data);
      case "overwriteFile":
        return handleOverwriteFile(data);
      case "renameFolder":
        return handleRenameFolder(data);
      default:
        throw new Error("Invalid action");
    }
  } catch (error) {
    return createErrorResponse(error.message);
  }
}

// Response creators
function createSuccessResponse(data) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "success",
    ...data
  })).setMimeType(ContentService.MimeType.JSON);
}

function createErrorResponse(message) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "error",
    message: message
  })).setMimeType(ContentService.MimeType.JSON);
}

// Action handlers
function handleCreateFolder(data) {
  if (!data.folderName) {
    throw new Error("Folder name is required.");
  }

  // Sanitize the folder name
  var sanitizedName = sanitizeFolderName(data.folderName);
  
  // Your folder ID from the Google Drive URL
  var root = DriveApp.getFolderById("1BD6fp88EQTwW9yhw4USkJjaRlbmeSHHa");
  
  // Check if a folder with the same name already exists
  var folders = root.getFoldersByName(sanitizedName);
  if (folders.hasNext()) {
    throw new Error("Folder already exists.");
  }
  
  // Create the new folder with sanitized name
  var newFolder = root.createFolder(sanitizedName);
  
  return createSuccessResponse({
    folderId: newFolder.getId()
  });
}

function handleCreateNestedFolder(data) {
  if (!data.parentFolderId || !data.folderName) {
    throw new Error("Parent folder ID and folder name are required.");
  }

  var folderId = createNestedFolder(data.parentFolderId, data.folderName);
  
  return createSuccessResponse({
    folderId: folderId
  });
}

function handleCreatePostulanteFolder(data) {
  if (!data.concursoFolderId || !data.folderName) {
    throw new Error("Concurso folder ID and folder name are required.");
  }

  var folderId = createNestedFolder(data.concursoFolderId, data.folderName);
  
  return createSuccessResponse({
    folderId: folderId
  });
}

function handleCreateDocFromTemplate(data) {
  if (!data.templateName || !data.folderId || !data.fileName || !data.data) {
    throw new Error("Template name, folder ID, file name, and data are required.");
  }
  
  // Get the template file
  var templateFile = DriveApp.getFileById(TEMPLATES[data.templateName]);
  
  // Create a copy in the destination folder
  var folder = DriveApp.getFolderById(data.folderId);
  var newDoc = templateFile.makeCopy(data.fileName, folder);
  
  // Get the document body as Google Docs document
  var doc = DocumentApp.openById(newDoc.getId());
  var body = doc.getBody();
  
  // Replace all placeholders
  for (var key in data.data) {
    body.replaceText('<<' + key + '>>', data.data[key] || '');
  }
  
  // Save and close the document
  doc.saveAndClose();
  
  return createSuccessResponse({
    fileId: newDoc.getId(),
    webViewLink: newDoc.getUrl()
  });
}

function handleUploadFile(data) {
  if (!data.folderId || !data.fileName || !data.fileData) {
    throw new Error("Folder ID, file name, and file data are required.");
  }
  
  // Decode base64 file data
  var blob = Utilities.newBlob(Utilities.base64Decode(data.fileData), "application/pdf", data.fileName);
  
  // Get the destination folder
  var folder = DriveApp.getFolderById(data.folderId);
  
  // Create the file
  var file = folder.createFile(blob);
  
  return createSuccessResponse({
    fileId: file.getId(),
    webViewLink: file.getUrl()
  });
}

function handleDeleteFile(data) {
  if (!data.fileId) {
    throw new Error("File ID is required.");
  }
  
  var file = DriveApp.getFileById(data.fileId);
  file.setTrashed(true);
  
  return createSuccessResponse({
    success: true
  });
}

function handleDeleteFolder(data) {
  if (!data.folderId) {
    throw new Error("Folder ID is required.");
  }
  
  var folder = DriveApp.getFolderById(data.folderId);
  folder.setTrashed(true);
  
  return createSuccessResponse({
    success: true
  });
}

function handleOverwriteFile(data) {
  if (!data.fileId || !data.fileData) {
    throw new Error("File ID and file data are required.");
  }
  
  var file = DriveApp.getFileById(data.fileId);
  
  // Decode base64 file data
  var blob = Utilities.newBlob(Utilities.base64Decode(data.fileData), file.getMimeType(), file.getName());
  
  // Update the file content
  file.setContent(blob.getBytes());
  
  return createSuccessResponse({
    fileId: file.getId(),
    webViewLink: file.getUrl()
  });
}

function handleRenameFolder(data) {
  if (!data.folderId || !data.newName) {
    throw new Error("Folder ID and new name are required.");
  }
  
  var folder = DriveApp.getFolderById(data.folderId);
  var sanitizedName = sanitizeFolderName(data.newName);
  folder.setName(sanitizedName);
  
  return createSuccessResponse({
    success: true
  });
}