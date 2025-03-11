// IMPORTANT: Make sure to add SECURE_TOKEN in Script Properties with the value from your .env file

// Function to sanitize folder name
function sanitizeFolderName(name) {
  // Replace spaces with underscores
  // Remove or replace special characters that might cause issues
  return name.replace(/\s+/g, '_')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '') // Remove accents
            .replace(/[^a-zA-Z0-9_-]/g, '_'); // Replace other special chars with underscore
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

// Web app entry point to handle POST requests.
function doPost(e) {
  try {
    // Parse the incoming JSON data.
    var params = JSON.parse(e.postData.contents);
    
    // Retrieve the secure token from script properties.
    var secureToken = PropertiesService.getScriptProperties().getProperty('SECURE_TOKEN');
    
    // Validate the token from the client.
    if (params.token !== secureToken) {
      throw new Error("Unauthorized request.");
    }
    
    var response = {
      status: "success"
    };
    
    // Handle different types of requests
    switch(params.action) {
      case 'createPostulanteFolder':
        response.folderId = crearPostulante(params.concursoFolderId, params.folderName);
        break;
      case 'createFolder':
        response.folderId = crearConcurso(params.folderName);
        break;
      case 'uploadFile':
        var uploadResult = uploadFile(params.folderId, params.fileName, params.fileData);
        response.fileId = uploadResult.fileId;
        response.webViewLink = uploadResult.webViewLink;
        break;
      case 'deleteFile':
        response.success = deleteFile(params.fileId);
        break;
      case 'deleteFolder':
        response.success = deleteFolder(params.folderId);
        break;
      case 'overwriteFile':
        var overwriteResult = overwriteFile(params.fileId, params.fileData);
        response.fileId = overwriteResult.fileId;
        response.webViewLink = overwriteResult.webViewLink;
        break;
      case 'renameFolder':
        response.success = renameFolder(params.folderId, params.newName);
        break;
      default:
        throw new Error("Unknown action: " + params.action);
    }
    
    return ContentService
      .createTextOutput(JSON.stringify(response))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    var errorResponse = {
      status: "error",
      message: err.message
    };
    return ContentService
      .createTextOutput(JSON.stringify(errorResponse))
      .setMimeType(ContentService.MimeType.JSON);
  }
}